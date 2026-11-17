---
name: windows-headless-winusb-bind
description: Bind a USB device to WinUSB when pyusb won't open it.
---

# Windows Headless WinUSB Bind (Secure Boot safe)

## Trigger
A USB device (e.g. Samsung download-mode 04E8:685D) shows as COMx/usbser and pyusb cannot claim the bulk endpoints (`LIBUSB_ERROR_NOT_SUPPORTED`), and the box has **Secure Boot ON** so unsigned/test-signing driver routes are dead.

## Key insight
You do NOT need a custom signed INF or to disable Secure Boot. `winusb.sys` is **Microsoft-signed and inbox**, so kernel policy is satisfied. Force the PnP device *node* (registry) to point at `WinUSB` instead of the class driver, then cycle the node so PnP reloads it. This is a binding override, not a driver install — no catalog, no pnputil, no signature wall.

## Steps (run elevated — Scheduled Task with /rl highest, or a P/Invoke elevated process)

### 1. Identify the device node instance ID
```powershell
Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like 'USB\VID_04E8*' }
# -> USB\VID_04E8&PID_685D\5&2169C787&0&1
```

### 2. Snapshot the current node (backup for reversibility)
```powershell
$key = 'HKLM:\SYSTEM\CurrentControlSet\Enum\USB\VID_04E8&PID_685D\<instance>'
$s = Get-ItemProperty $key
@{Service=$s.Service;ClassGUID=$s.ClassGUID;Driver=$s.Driver}
 | ConvertTo-Json | Out-File winusb_backup.json -Encoding utf8
```

### 3. Force the node to WinUSB
```powershell
$usbclass = '{88BAE032-5A81-49f0-BC3D-A4FF138216D6}'   # WinUSB Device class
$intfGuid = '{F72FE0D4-CBCB-407D-8814-9ED673D0DD6B}'   # device interface GUID
Set-ItemProperty -Path $key -Name Service   -Value 'WinUSB' -Type String -Force
Set-ItemProperty -Path $key -Name ClassGUID -Value $usbclass -Type String -Force
Set-ItemProperty -Path $key -Name Class     -Value 'USBDevice' -Type String -Force
$dp = Join-Path $key 'Device Parameters'; New-Item -Path $dp -Force | Out-Null
Set-ItemProperty -Path $dp -Name DeviceInterfaceGUIDs -Value $intfGuid -Type MultiString -Force
```
ClassGUID may get re-resolved by PnP back to the original class — that's cosmetic. **Only the `Service=WinUSB` value carries the bind.**

### 4. Cycle the node
```powershell
Disable-PnpDevice -InstanceId $inst -Confirm:$false
Start-Sleep 2
Enable-PnpDevice  -InstanceId $inst -Confirm:$false
(Get-PnpDeviceProperty -InstanceId $inst -KeyName 'DEVPKEY_Device_Service').Data   # -> WinUSB
```

### 5. Verify pyusb can now open it
```python
import usb.core
dev = usb.core.find(idVendor=0x04E8, idProduct=0x685D)
cfg = dev.get_active_configuration()          # must not throw
for itf in cfg:
    print(itf.bInterfaceNumber, itf.bInterfaceClass)  # iface 1 class 0x0A = CDC data w/ bulk pair
```

## Expected descriptor (Samsung download mode)
- iface 0: class 0x02 (CDC ACM control), ep 0x82 IN
- iface 1: class 0x0A (CDC data), ep 0x81 IN + 0x01 OUT @ 512 bytes  <- the ODIN/LOKE bulk pair

## Pitfalls
1. **Never run non-elevated** — registry writes to `\System\CurrentControlSet\Enum` need admin. Direct `ssh powershell` is non-elevated; use `schtasks /create /tn X /tr "<cmd>" /sc once /st 23:59 /rl highest /f` then `/run`. Add an outer `.cmd` that calls `powershell -File` and redirects output to a log you read back (execution-policy blocks bare `.ps1`).
2. **`UpdateDriverForPlugAndPlayDevicesW` alone returns 0x103 (ERROR_NO_MORE_ITEMS)** unless the INF is already staged in the DriverStore. The registry-node override + cycle is the reliable headless route.
3. **`pnputil /add-driver` rejects unsigned INFs** even when the referenced `winusb.sys` is signed — it checks the *catalog*. Don't fight it; use the registry override.
4. **Injecting `USB\MS_COMP_WINUSB` into CompatibleIDs does NOT force a rebind** — PnP won't re-match a driver-bound node from a registry edit alone; only a physical replug or node cycle does. Node cycle + Service override is what works.
5. **Device string reads garbage (Љ)** — download-mode descriptors are raw bytes, fix with `set PYTHONIOENCODING=utf-8`; cosmetic.
6. **On Linux no rebind is needed** — libusb just works; this procedure is Windows-only.
7. **BitLocker danger**: if you planned to disable Secure Boot or flip boot config, suspend BitLocker first (`manage-bde -protectors -disable C:`) or the next reboot trips a recovery screen and you lose remote access.

## Verified result
On a Dell Windows 11 (26200, Secure Boot ON) with Samsung A54 04E8:685D in download mode: after node override + cycle, `Service=WinUSB`, pyusb opened the device, and `protocol.py`'s `connect()` handshake succeeded — `[INFO] ODIN/LOKE handshake successful`, `[INFO] Found bulk interface[1]: IN=0x81 OUT=0x01`, `[INFO] Claimed interface 1`.

## ODIN protocol framing (reverse-engineered from Heimdall source; verified live)
Response packets: control type echo @0, value @4 (Heimdall `kDataSize=4`).
- SessionSetup (0x64): begin@0, deviceType@1, totalBytes@2, filePartSize@5.
- PIT (0x65): request @4; request dump=1, part=2, endTransfer=3. PIT file size returned @4 (NOT @0). `ReceiveFilePartPacket::kDataSize=500` (parts, not 512).
- FileTransfer (0x66): flash=0, dump=1, part=2, end=3.
  - Begin seq: `pkt(0x66,2,seqByteCount)`.
  - Data: raw chunks (1 MiB), empty bulk transfer (0 bytes) BEFORE each part after the first (Heimdall `kEmptyTransferBefore`). Part response partIndex @4.
  - EndPhoneFileTransferPacket (single packet, 8 dwords): `[0x66, 3, dest=0, seqByteCount, 0, deviceType=AP(4), fileIdentifier, endOfFile(0/1)]`. timeouts on end/reboot after a write = device processing write, may wedge.
- Empty-transfer quirk is mandatory on file-part sends or the device stalls.

## MTK/Samsung PIT entry layout (mt6765)
32-byte header: magic `0x12349876` @0, entry_count @4, 24-byte board string @8. 128-byte entries; for MTK the name is @0, flash filename @0x20, geometry dwords ~@0x64 (identifier, block size/count). `misc` identifier typically 0x16 (22). Board string like `COM_TAR2MTK6765` = MediaTek Helio P35 (A03s/A12/M04/F04-class), NOT an Exynos A54.

