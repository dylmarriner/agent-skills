# Samsung download-mode: ODIN protocol, MTK vs Exynos, and write lanes

Session-verified detail for Samsung Galaxy phones over USB download mode (ODIN bulk protocol,
Android and MTK chipsets). Covers device identification, the ODIN frame layout, and the
critical fact that the *write* lane differs by chipset.

## ⚠️ Rule that governs this whole class (Dylan correction)

**Identify the connected device from its OWN PIT before any write. Never assume the model from
memory, prior sessions, or the device name.** The phone physically on the cable is the only
ground truth. The attached device is frequently NOT the one your notes describe.

Symptom of getting this wrong: you spend the session re-plumbing an ODIN flush for the wrong
chipset, or flash-gate on a model that isn't connected. Both wasted real effort here.

## Device identification from the PIT

After the ODIN handshake + session, send a PIT dump request and decode the 32-byte PIT header:

```
PIT header (32 bytes, magic 0x12349876 @0):
  @0   u32 magic            = 0x12349876
  @4   u32 entry_count
  @8   char[24] board string  <- THE identifier
```

- **Exynos Samsung** (A54, S24, etc.): partitions like `BOOT`, `SYSTEM`, `UP_`, `efs`, `misc`.
- **MTK Samsung** (Galaxy A03/A03s/A12/M04/A05/A05s): board string like `COM_TAR2MTK6765`
  (contains `MTK`), partitions `pgpt`, `preloader`, `scp`, `md1img`, `tee`, `lk`, `efuse`,
  `dtbo`, `misc`, `super`, `btd`, `w0`.
- Booted-Android state enumerates as `04E8:6860` (MTP composite + modem); the serial lands in
  the instance ID (e.g. `USB\VID_04E8&PID_6860\R94Y507A8YJ`).
- Download-mode state enumerates as `04E8:685D`.

Board string ↔ model map (MT6765 = Helio P35): `COM_TAR2MTK6765` → Galaxy A-family MTK,
`SM-A055F` = Galaxy A05, `SM-A037F` = A03s, `SM-A125F` = A12. These MT6765 Samsungs use the
MTK partition schema above, NOT Exynos.

## ODIN protocol frame layout (verified against Heimdall source)

Packets are 1024-byte little-endian. Responses echo the control type @0 and put the value @4
(Heimdall `ResponsePacket::kDataSize = 4` — ALWAYS read the result/size at offset 4, not 0).

- SessionSetup (0x64): begin=0, deviceType=1, totalBytes=2, filePartSize=5.
- PIT (0x65): request @4; dump=1, part=2, endTransfer=3. **PIT file size is at offset 4**
  (reading offset 0 yields the control echo 0x65 = 101, a classic bug). Parts are 500 bytes
  (`ReceiveFilePartPacket::kDataSize`), not 512.
- FileTransfer (0x66): flash=0, dump=1, part=2, end=3.
  - Begin sequence: `pkt(0x66, 2, sequenceByteCount)`.
  - Data: raw 1 MiB chunks. **Empty-transfer quirk**: send a zero-length bulk transfer BEFORE
    each part after the first (`kEmptyTransferBefore`). Batch-response partIndex is @4.
  - EndPhoneFileTransferPacket = one 8-dword packet:
    `[0x66, 3, dest=0, seqByteCount, 0, deviceType=AP(4), fileIdentifier, endOfFile(0/1)]`.

PIT file-size must be read from offset 4. If your Python reads 101 bytes where the device said
16384, that's the offset-4 bug.

## The critical finding: write lane is chipset-specific

- **ODIN raw-PIT-identifier write is the EXYNOS lane.** On an MTK Samsung it fails: the device
  ACKs the flash init + sequence begin (`66 00 00 00`), then **NAKs every data chunk with
  `0xFFFFFFFF`**. This is a protocol-layer mismatch, not a fixable frame bug. Do not keep
  re-firing frames at it.
- MTK Samsungs are flashed via **mtkclient in BROM mode** (VID `0E8D:0003`), or via Samsung
  Odin with a proper **firmware package** (BL/AP/CP/CSC) for the exact model. Raw-slot ODIN
  writes are the wrong lane for these chipsets.
- To enter BROM: power off completely, then hold **Vol+ and Vol- together** (or all buttons)
  while connecting USB. If it boots to the Samsung ODIN screen or to Android instead, you did
  not hit BROM.

## Headless WinUSB bind (needed on Secure-Boot Windows so pyusb can claim the ODIN bulk pair)

`winusb.sys` is Microsoft-signed + inbox, so no custom signed INF, no Secure Boot disable, no
test-signing. Instead override the PnP node's `Service` to `WinUSB` and cycle the node:

```powershell
$key='HKLM:\SYSTEM\CurrentControlSet\Enum\USB\VID_04E8&PID_685D\<instance>'
Set-ItemProperty $key -Name Service -Value 'WinUSB' -Type String -Force
Set-ItemProperty $key -Name ClassGUID -Value '{88BAE032-5A81-49f0-BC3D-A4FF138216D6}' -Type String -Force
Set-ItemProperty $key -Name Class -Value 'USBDevice' -Type String -Force
Disable-PnpDevice -InstanceId $inst -Confirm:$false; Start-Sleep 2
Enable-PnpDevice  -InstanceId $inst -Confirm:$false
```

- Must run ELEVATED: on a remote box use `schtasks /create /rl highest /sc once` then `/run`
  (bare `ssh powershell` is non-elevated; bare `.ps1` is blocked by execution policy — use a
  `.cmd` wrapper calling `powershell -File`).
- `pnputil /add-driver` rejects unsigned INFs (checks the catalog) — don't fight it.
- `UpdateDriverForPlugAndPlayDevicesW` returns 0x103 unless the INF is already staged in the
  DriverStore. The node override + cycle is the reliable headless path.
- Injecting `USB\MS_COMP_WINUSB` into CompatibleIDs does NOT force a rebind — only a node cycle
  or physical replug works.
- After bind, pyusb sees iface 1 (class 0x0A) with the ODIN bulk pair (0x81 IN / 0x01 OUT).
- Single-session firmware: each probe opens a fresh session; if a probe aborts, the download
  firmware wedges and needs a node cycle (or physical re-entry) to reset before the next
  handshake. Always reset/cycle between runs.

## Default factory reset for a booted Samsung

If the device booted to Android (MTP `04E8:6860`), you don't need BROM at all for a reset:
power off, hold **Vol+ + Power** to enter recovery, select "Wipe data/factory reset". ADB is
unavailable on a locked/pre-setup device. MTP storage may fail to mount on the Dell if the
`WUDFRd` (user-mode driver) host is stuck — that's a host-side cosmetic issue, cycle the MTP
interface node or restart WUDFHost; it does NOT mean the phone is broken.
