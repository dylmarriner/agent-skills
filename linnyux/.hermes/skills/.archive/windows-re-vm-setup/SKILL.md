---
name: windows-re-vm-setup
description: Set up a QEMU/KVM Windows VM for running reverse engineering tools (unlock tools, mobile servicing software, SIM installer payloads). Covers libvirt config, virtio drivers, networking, RDP access, Tailscale, and file transfer patterns.
trigger: When the user needs a Windows VM for reverse engineering, mobile unlocking tools, or running Windows-only RE software (Hydra Tool, Octoplus, Apizu, Chimera, TFTUnlock, etc.).
---

# Windows RE VM Setup

Class of work: provisioning a KVM-accelerated Windows VM to run RE/mobile-unlocking tools that don't work under Wine (Smart Install Maker, dongle-protected software, USB device tools).

## Core Principles

- **KVM, not TCG** — soft emulation (TCG) is too slow for Windows install/use. Always use `accel=kvm`.
- **Network first** — don't fight with Windows firewall via keyboard injection. Give the user instructions or set up Tailscale inside the VM for direct access.
- **Keyboard injection is unreliable** — `virsh send-key` works for simple inputs but fails on UAC dialogs, installer wizards, and focus-dependent UI. Use RDP or SPICE instead.
- **SPICE client**: Use `spicy -h 127.0.0.1 -p <port>` as the primary SPICE viewer. It's a dedicated SPICE client from the `spice-client-gtk` package — always works, zero protocol registration issues. `virt-viewer <vm>` also works. `remote-viewer spice://...` can fail with "SPICE protocol not registered" errors because its URI handler registration depends on the desktop environment.

## VM Creation

### Preferred: virt-install (one-liner)

For initial VM creation, use `virt-install` — it handles firmware, SATA controller, TPM, and boot order correctly:

```bash
virt-install --name windows11 --ram 4096 --vcpus 2 --cpu host-passthrough \
  --disk /var/lib/libvirt/images/win11.qcow2,bus=sata,size=60 \
  --cdrom /var/lib/libvirt/images/Win11.iso \
  --os-variant win11 \
  --boot uefi \
  --graphics spice,listen=127.0.0.1 \
  --tpm backend.type=emulator,model=tpm-crb,version=2.0 \
  --noautoconsole
```

After creation, you can dump the XML and tweak manually:
```bash
virsh dumpxml windows11 > /tmp/windows11.xml
# (edit parser)
virsh define /tmp/windows11.xml
```

### Manual XML (when fine-tuning)

| Component | Recommendation |
|-----------|---------------|
| CPU | Host passthrough, 2 vCPUs |
| RAM | 4GB minimum (6GB preferred for RE tool suites) |
| Disk | 60GB+ qcow2 (Windows 11 + tools is ~40GB) |
| Chipset | Q35 (modern, supports PCIe, SATA, virtio) |
| Firmware | OVMF (UEFI) with Secure Boot — **REQUIRED by Windows 11** |

### Networking Strategy

Windows 11 has no built-in virtio drivers. To get networking during/after install:

**Option A: e1000e NIC (works out of box)**
```bash
virsh attach-interface <vm> network default --model e1000e --config
```
Windows 11 has Intel PRO/1000 drivers built-in — works immediately.

**Option B: virtio NIC (faster, needs driver install)**
Attach a virtio-win ISO as CDROM:
```bash
# Download virtio drivers
wget -O /tmp/virtio-win.iso "https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/archive-virtio/virtio-win-0.1.262-1/virtio-win-0.1.262.iso"

# Attach to VM (requires VM to be off for SATA bus)
virsh attach-disk <vm> /tmp/virtio-win.iso sdc --type cdrom --mode readonly --config
```

**Best practice:** Add BOTH NICs — e1000e for immediate network access, virtio for speed after driver install. Use unique MAC addresses.

### MAC Address Pitfall

Never give two NICs the same MAC address. Windows gets confused. Generate unique MACs:
```bash
# libvirt auto-generates if you don't specify, or use a unique suffix:
# NIC 1: 52:54:00:76:c3:3b
# NIC 2: 52:54:00:77:c3:3b
```

## Post-Install Configuration

### Enable RDP + Open Firewall

Give the user these commands to run in an **Admin Command Prompt** (Win+R → `cmd` → Ctrl+Shift+Enter):
```
netsh advfirewall set allprofiles state off
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f
```

### Install Virtio Drivers

Attach the virtio-win ISO and have the user run `D:\virtio-win-gt-x64.msi` with defaults. This enables:
- NetKVM (virtio network — 2-3x faster than e1000e)
- Balloon (dynamic memory)
- QXL/SPICE (proper display driver — screenshots work)

### Tailscale Inside VM

If Windows Firewall is blocking RDP and keyboard injection isn't working, the simplest fix is installing Tailscale inside the VM. This gives:
- A routable 100.x.x.x IP that's not subject to Windows Firewall (Tailscale tunnels through)
- Direct SSH/RDP access from the host
- No port forwarding needed

On the host, once Tailscale is running in the VM:
```bash
tailscale status | grep -i <vm-name>
timeout 3 bash -c 'echo >/dev/tcp/<tailscale-ip>/3389' && echo "RDP reachable via Tailscale"
```

## Cold Boot Sequence

Step-by-step for starting and reaching the desktop:

1. `virsh start <vm>` — boot the VM (KVM, ~15-30s to Windows lock screen).
2. Check Tailscale reconnection: `tailscale status | grep <vm-name>` — the node should flip from "offline, last seen …" to "-" (transitioning) to "active".
3. Ping the Tailscale IP to confirm network: `tailscale ping <hostname>`.
4. **Diagnose the screen state without vision**: `virsh screenshot <vm> /tmp/boot.png && tesseract /tmp/boot.png stdout`. OCR reads the lock screen text (PIN prompt, update screen, desktop, etc.) without needing a vision-capable model. Far faster than blind RDP polling.
5. If at PIN/lock screen → log in via SPICE: `spicy -h 127.0.0.1 -p <port>` (or `virt-viewer <vm>`). Find the SPICE port with `ss -tlnp | grep <port>` or from `virsh dumpxml <vm> | grep spice`. `virsh send-key` is documented below but unreliable on PIN fields.
6. Once at desktop, verify RDP: `timeout 3 bash -c 'echo >/dev/tcp/<tailscale-ip>/3389' && echo "RDP OPEN"`.

## Interacting with the VM

### Preferred: RDP via xfreerdp
```bash
xfreerdp /v:<tailscale-ip> /u:<username> /p:<password> /dynamic-resolution +clipboard
```

### Screenshot monitoring

```bash
virsh screenshot <vm> /tmp/screenshot.png
file /tmp/screenshot.png   # check resolution (1280x800 typical)

# OCR the screenshot to read screen state — works without vision model
tesseract /tmp/screenshot.png stdout
# Lock screen yields: "Enter your PIN", "forgot my PIN", username
# Desktop yields: app text, taskbar labels, error dialogs
```

### Keyboard input (last resort — unreliable for complex UIs)
```bash
# Simple text entry
virsh send-key <vm> KEY_H KEY_E KEY_L KEY_L KEY_O

# Ctrl+Alt+Del
virsh send-key <vm> KEY_LEFTCTRL KEY_LEFTALT KEY_DELETE

# Win+R (Run dialog)
virsh send-key <vm> KEY_LEFTMETA KEY_R

# UAC confirmation (Alt+Y)
virsh send-key <vm> KEY_LEFTALT KEY_Y
```
⛔ Keyboard injection doesn't work for: UAC dialogs (sometimes), MSI installer wizards, focus-dependent UI elements, password/PIN fields on lock screen.

## Enable SSH Server (Windows 10/11)

When the VM needs SSH access from your Tailscale mesh, OpenSSH Server is not installed by default on Windows. The install requires admin privileges.

**THIS CANNOT BE DONE FROM HOST KEYBOARD INJECTION** — admin UAC elevation steals focus and subsequent key presses go to the wrong window. You must run the commands inside the VM (via SPICE/virt-viewer, or from a local desktop session).

From an **Admin PowerShell** (right-click Start → Terminal (Admin) or PowerShell (Admin)), run:

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
New-NetFirewallRule -Name 'OpenSSH-Server' -DisplayName 'OpenSSH Server' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

Or use the included script `scripts/Enable-OpenSSH.ps1` — SCP it to the VM and run from Admin PowerShell:

```bash
scp -o StrictHostKeyChecking=no /path/to/Enable-OpenSSH.ps1 reher@100.x.x.x:'C:\\Users\\reher\\Downloads\\'
ssh reher@100.x.x.x "powershell -ExecutionPolicy Bypass -File 'C:\\Users\\reher\\Downloads\\Enable-OpenSSH.ps1'"
```

Once installed, SSH from any Tailscale peer:
```bash
ssh <username>@<tailscale-ip>
```

**Username pitfall**: The PIN-login user and the active SSH user may have different usernames on the same VM (e.g. PIN login `re`, SSH username `reher`). If `ssh re@<ip>` connects but drops you immediately or the command produces no output, try `reher` or check with `whoami` inside the VM. Both accounts exist — Microsoft account vs local user difference.

The included script `scripts/Enable-OpenSSH.ps1` automates this — see the SSH section for transfer/run commands.

## File Transfer to VM

### Via SCP (requires SSH server on Windows)

```bash
# Push a file/installer TO the Windows VM
scp -o StrictHostKeyChecking=no /path/to/file.exe user@<tailscale-ip>:'C:\\Users\\<user>\\Downloads\\'

# Pull a file FROM the Windows VM
scp -o StrictHostKeyChecking=no user@<tailscale-ip>:'C:\\path\\to\\file' /tmp/
```

Note: SCP on Windows writes to `C:\Users\<user>\` only — system paths (`C:\Program Files`, `C:\Windows`) require admin and will fail with permission denied. Use SSH + PowerShell for admin paths.

### Via SSH + PowerShell (admin paths)

```bash
ssh user@<tailscale-ip> "powershell -Command \"Move-Item 'C:\\Users\\user\\Downloads\\file.exe' 'C:\\Tools\\' -Force\""
```

Double-escape — outer quotes for cmd.exe, inner quotes for PowerShell. Use single backslashes inside the PowerShell -Command string; they don't need escaping.

### Via RDP clipboard
```bash
xfreerdp /v:<ip> /u:<user> /p:<pass> /drive:linux,/path/to/files
```
Mounts Linux directory as a network drive in Windows Explorer.

### Via SMB (if network works)
```bash
# Host shares files
sudo apt-get install -y samba
# Configure share, then access from Windows via \\192.168.122.1\share
```

### Via CDROM (for ISOs)
```bash
virsh attach-disk <vm> /path/to/file.iso sdd --type cdrom --mode readonly --config
# Shut down VM first — SATA can't be hotplugged
```

## Windows ISO Download — ORDER OF PREFERENCE

### 1st: Official Microsoft ISO (preferred — always works)

If an official Windows ISO was previously downloaded, check standard locations on the KVM host:

```bash
find /home -name '*.iso' -size +1G -type f 2>/dev/null
find /mnt -name '*.iso' -size +1G -type f 2>/dev/null
find /var/lib/libvirt/images -name '*.iso' -size +1G -type f 2>/dev/null
```

Official Microsoft ISOs have proper UEFI boot support and work reliably with OVMF+KVM.

### 2nd: massgrave.dev (reliable, always up-to-date)

Microsoft's official download page is JavaScript-heavy and often returns a stub. Use massgrave.dev for direct download links:

```
https://massgrave.dev/windows_11_links.html
```

The page has tabs for Consumer/Business/IoT/ARM64. The en-us link format is:
```
https://zerofs.link/f/<current-id>/
```

**⚠️ zerofs.link Cloudflare caveat:** The actual download links go through zerofs.link which has Cloudflare Turnstile captcha ("Verify you are human"). This blocks curl/wget/aria2 downloads. The browser automation route also fails — clicking the checkbox requires solving the captcha. Try `warp` VPN (as massgrave suggests) or use the uupdump method below as a fallback.

### uupdump.net (alternative — no captcha, works from Linux)

When massgrave/zerofs is blocked by Cloudflare, use uupdump — but note that the Linux converter ISOs are known to have boot issues in KVM (see next section).

1. Navigate to https://uupdump.net/
2. Click "Latest Public Release build" → **x64**
3. Select language → English (United States)
4. Select editions (Home + Pro is sufficient)
5. On the summary page, select **"Download UUP set"** (the ISO conversion option requires Windows).
   Do NOT select "Download and convert to ISO" — that option says "Windows is required to create the ISO image".
6. Click "Create download package" — browser downloads a ZIP containing:
   - `uup_download_linux.sh` — bash script using aria2
   - `uup_download_macos.sh` — macOS version
   - `uup_download_windows.cmd` — Windows version
   - `readme.unix.md` — instructions
   - `files/` — support scripts
7. Run the download script:
   ```bash
   unzip 26200.*.zip -d /tmp/windows-iso
   cd /tmp/windows-iso
   chmod +x *.sh
   ./uup_download_linux.sh   # downloads ~10GB from Microsoft CDNs via aria2
   ```
8. **Convert to ISO** — download creates a `UUPs/` subdirectory. Convert with the converter:
   ```bash
   # Get the converter (from uupdump's git repo)
   git clone https://git.uupdump.net/uup-dump/converter.git /tmp/uup-converter
   # Run conversion: convert.sh [compression] [uups_dir] [virtual_editions]
   cd /tmp/uup-converter && bash convert.sh wim /tmp/windows-iso/UUPs/ 0
   ```
   **⚠️ Correct syntax**: `convert.sh wim <dir> 0` — the `-u, -o, -w` flags do NOT exist.
   - `wim` = standard compression, `esd` = solid compression
   - `0` = no virtual editions, `1` = create virtual editions
   - Output ISO appears in the converter directory (e.g. `26100.1_MULTI_X64_EN-US.ISO`)

9. **⚠️ UUP converter ISO is known to fail booting in KVM** — The converter produces an ISO that lacks proper UEFI boot support in the El Torito catalog. Even after adding efisys.bin and using xorriso with `-isohybrid-gpt-basdat`, OVMF consistently reports "No bootable option or device was found." Numerous machine types (q35, i440fx), disk buses (SATA, IDE, virtio), and firmware types (OVMF with/without Secure Boot, SeaBIOS) were tested with no success. The Windows setup never launched (disk remained at 200-328KB). **If you need a working VM, use an official Microsoft ISO.**

10. **(Optional) Embed autounattend.xml for unattended install** — inject an answer file into boot.wim to skip OOBE, create a local admin, and prevent BitLocker auto-enable:
   ```bash
   # Extract ISO contents to a working directory
   mkdir -p /tmp/iso_mount /tmp/iso_edit
   mount -o loop /path/to/downloaded.iso /tmp/iso_mount
   rsync -a /tmp/iso_mount/ /tmp/iso_edit/
   umount /tmp/iso_mount
   
   # Copy boot.wim to writable location
   cp /tmp/iso_edit/sources/boot.wim /tmp/boot.wim
   
   # Mount index 2 (Windows Setup image) read-write
   wimlib-imagex mountrw /tmp/boot.wim 2 /tmp/wim_mount --allow-other
   
   # Copy autounattend.xml to WIM root AND Sysprep dir
   cp autounattend.xml /tmp/wim_mount/
   mkdir -p /tmp/wim_mount/Windows/System32/Sysprep
   cp autounattend.xml /tmp/wim_mount/Windows/System32/Sysprep/
   
   # Commit changes and replace boot.wim
   wimlib-imagex unmount /tmp/wim_mount --commit
   cp /tmp/boot.wim /tmp/iso_edit/sources/boot.wim
   ```
   
   Sample `autounattend.xml` (creates user RE / pass re123, skips OOBE, no BitLocker):
   ```xml
   <?xml version="1.0" encoding="utf-8"?>
   <unattend xmlns="urn:schemas-microsoft-com:unattend">
       <settings pass="windowsPE">
           <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" ...>
               <DiskConfiguration>
                   <Disk wcm:action="add">
                       <CreatePartitions>
                           <CreatePartition wcm:action="add"><Order>1</Order><Type>Primary</Type><Size>60000</Size></CreatePartition>
                       </CreatePartitions>
                       <ModifyPartitions>
                           <ModifyPartition wcm:action="add"><Order>1</Order><Active>true</Active><Format>NTFS</Format><Label>Windows</Label><Letter>C</Letter><PartitionID>1</PartitionID></ModifyPartition>
                       </ModifyPartitions>
                       <DiskID>0</DiskID><WillWipeDisk>true</WillWipeDisk>
                   </Disk>
               </DiskConfiguration>
               <ImageInstall>
                   <OSImage>
                       <InstallFrom><MetaData wcm:action="add"><Key>/IMAGE/INDEX</Key><Value>6</Value></MetaData></InstallFrom>
                       <InstallTo><DiskID>0</DiskID><PartitionID>1</PartitionID></InstallTo>
                   </OSImage>
               </ImageInstall>
               <UserData><AcceptEula>true</AcceptEula><FullName>RE</FullName><Organization>RE</Organization></UserData>
           </component>
       </settings>
       <settings pass="oobeSystem">
           <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" ...>
               <AutoLogon><Password><Value>re123</Value><PlainText>true</PlainText></Password><Enabled>true</Enabled><Username>RE</Username></AutoLogon>
               <UserAccounts><LocalAccounts>
                   <LocalAccount wcm:action="add">
                       <Password><Value>re123</Value><PlainText>true</PlainText></Password>
                       <Group>Administrators</Group><DisplayName>RE</DisplayName><Name>RE</Name>
                   </LocalAccount>
               </LocalAccounts></UserAccounts>
               <OOBE>
                   <HideEULAPage>true</HideEULAPage><SkipMachineOOBE>true</SkipMachineOOBE>
                   <SkipUserOOBE>true</SkipUserOOBE><ProtectYourPC>3</ProtectYourPC>
                   <NetworkLocation>Work</NetworkLocation><HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE>
                   <!-- ⚠️ CRITICAL for Win11 25H2+: without this, OOBE still forces MS account signup -->
                   <HideOnlineAccountScreens>true</HideOnlineAccountScreens>
               </OOBE>
           </component>
       </settings>
   </unattend>
   ```

10. **Repack ISO with UEFI boot support** (required for the autounattend to be found at boot):
    ```bash
    cd /tmp/iso_edit
    genisoimage -o /var/lib/libvirt/images/Win11_unattended.iso \
      -b boot/etfsboot.com -no-emul-boot -boot-load-size 8 \
      -eltorito-alt-boot -e efi/microsoft/boot/efisys.bin -no-emul-boot \
      -V 'Win11_RE' \
      .
    ```
    This takes ~10 minutes for a 4GB ISO. **⚠️ Use `-e` not `-b` under `-eltorito-alt-boot`** — `-b` specifies the x86 BIOS boot image, `-e` specifies the UEFI boot image (efisys.bin). Using `-b` for both produces an ISO that OVMF can't boot ("No bootable option or device was found").

11. **Define VM with the unattended ISO** — attach as SATA CDROM, set `boot dev='cdrom'` first. See "Q35 SATA Controller" pitfall below.

See `references/download-sources.md` for the full procedure, including fresh-install registry tweaks to bypass BitLocker, TPM checks, and the Microsoft Account requirement — all critical for setting up an RE VM that doesn't lock you out.

## Tool Installation via winget

Windows 11 ships with `winget` — the native package manager. Use it for quick tool installs on a clean VM.

```bash
# From SSH or directly in the VM
ssh reher@<tailscale-ip> "powershell -Command \"winget install 7zip.7zip --silent --accept-package-agreements\""

ssh reher@<tailscale-ip> "powershell -Command \"winget install Google.Chrome --silent --accept-package-agreements\""

# Check winget for any tool
ssh reher@<tailscale-ip> "powershell -Command \"winget search <toolname>\""
```

Common RE-adjacent winget packages:

| Package | winget ID | Purpose |
|---------|-----------|---------|
| 7-Zip | `7zip.7zip` | Extract RAR, 7z, ZIP (RAR5 support) |
| Google Chrome | `Google.Chrome` | Browser for tool portal downloads |
| Notepad++ | `NotepadPlusPlus.NotepadPlusPlus` | Text/hex viewing |
| HxD (note: may need manual download) | — | Hex editor |
| Process Explorer | `Microsoft.Sysinternals.ProcessExplorer` | Process inspection |

**Pitfall**: `winget` runs in user context — some installers trigger UAC and silently fail. Check success with `where <toolname>` after install.

## RAR Archive Corruption Diagnostics

Many RE tool installers ship as RAR archives found on file-sharing sites. Partial/truncated downloads are common.

**Symptoms of a truncated RAR:**

| Check | Command | Truncated Indicator |
|-------|---------|-------------------|
| File size | `ls -lh file.rar` | Much smaller than expected (e.g. 3.4MB vs 2GB) |
| Physical Size | `7z l file.rar` | claims huge size (e.g. 2018700604) but file is tiny |
| Extract | `unrar t file.rar` | "Unexpected end of archive", "checksum error" |
| Compress method | `7z x file.rar` | "Unsupported Method" error — often a red herring, the actual cause is truncation |

**Diagnostic one-liner:**
```bash
7z l file.rar 2>&1 | grep -E 'Physical Size|Type|Method'
```

If Physical Size is wildly larger than the actual file, the download was truncated.
If Method shows compression the local 7z doesn't support, try on Windows with 7-Zip (which may handle newer RAR5). If Windows 7-Zip also fails with "Data Error", the file is definitely corrupt.

**Solution**: Re-download from the original source. RE tool RAR sizes vary:
- Hydra Tool V7.0: ~2GB (contains embedded SM-installer EXE)
- Octoplus: typically 500MB-1GB
- TFTUnlock: typically 100-500MB
- Chimera: typically 200-500MB

## BitLocker Recovery — Accessing an Encrypted/PIN-Locked VM

When the Windows VM has BitLocker with Windows Hello PIN and you don't know the PIN:

### Step 1: Trigger Windows Recovery Environment

Interrupt the boot **3 times** by power-cycling before Windows fully loads. Each reset after Windows has started loading marks a failed boot attempt. On the 3rd failed boot, Windows automatic repair kicks in.

```bash
# From the host (kubuntux or libvirt host)
virsh start windows11
sleep 15  # let Windows start loading
virsh reset windows11
sleep 15
virsh reset windows11
sleep 15
virsh reset windows11

# Wait ~90s for WinRE to appear
sleep 90
virsh screenshot windows11 /tmp/boot.png
tesseract /tmp/boot.png stdout
# Expected: "Your device ran into a problem and couldn't be repaired"
```

### Step 2: Navigate WinRE to Command Prompt

Use `virsh send-key` to navigate through recovery menus:

```bash
# Press Enter at recovery screen to see options
virsh send-key windows11 KEY_ENTER
sleep 5

# Screenshot to confirm
virsh screenshot windows11 /tmp/winre.png
```

The WinRE menu has: **Continue**, **Troubleshoot**, **Turn off your PC**. Navigate with Tab/Arrow keys:
- Troubleshoot → Advanced Options → Command Prompt

### Step 3: Utilman Swap (Sticky Keys Trick)

At the WinRE Command Prompt, the C: drive is typically available (BitLocker auto-unlocked by TPM during boot):

```cmd
# Check available drives
diskpart
list volume
exit

# Navigate to System32
C:
cd Windows\System32

# Backup and replace utilman.exe with cmd.exe
ren utilman.exe utilman.exe.bak
copy cmd.exe utilman.exe

# Reboot
wpeutil reboot
```

**The VM reboots normally to the PIN screen.** Click the Ease of Access icon (accessibility button on the lock screen) → **cmd.exe runs as SYSTEM**. From there:
```cmd
# Create a new local admin account
net user admin Password123! /add
net localgroup Administrators admin /add

# Or enable built-in Administrator
net user Administrator /active:yes
net user Administrator Password123!

# Or reset PIN without knowing old one (this command removes PIN requirement)
net user kubuntux NewPassword123!
```

### Alternative: Boot from Windows Install ISO

If WinRE access fails, attach a Windows 11 ISO and boot from it:

```bash
# Download Windows 11 ISO
wget -O /tmp/Win11_24H2.iso "https://software.download.prss.microsoft.com/dbazure/Win11_24H2_English_x64.iso"
virsh attach-disk windows11 /tmp/Win11_24H2.iso sdd --type cdrom --mode readonly --config
virsh destroy windows11
virsh start windows11
```

At the Windows Setup screen, press **Shift+F10** (via virsh send-key) to get a command prompt, then follow the same utilman swap from Step 3.

### SPICE Port Discovery

To connect to the VM's display directly when RDP/Tailscale aren't available:

```bash
virsh qemu-monitor-command windows11 --hmp 'info spice'
# Returns: address: 127.0.0.1:5901, auth: none

# Connect directly with SPICE client
spicy -h 127.0.0.1 -p 5901
```

This bypasses all network/firewall issues — SPICE is the VM's native display protocol.

## Direct Disk Access via qemu-nbd

When you need to read/write the VM's disk image without booting it (for BitLocker analysis, file extraction, or registry hacking):

```bash
# Stop the VM
virsh destroy windows11

# Load NBD kernel module
modprobe nbd max_part=8

# Connect the qcow2 as a block device
qemu-nbd --connect=/dev/nbd0 /var/lib/libvirt/images/windows11.qcow2

# Partitions appear as /dev/nbd0p1, p2, p3, etc.
lsblk /dev/nbd0
fdisk -l /dev/nbd0

# Mount non-encrypted partitions directly
mount /dev/nbd0p1 /mnt/efi     # EFI partition (vfat)
mount /dev/nbd0p4 /mnt/recovery # Recovery partition (NTFS)

# For BitLocker-encrypted partitions (Windows 11 C: drive):
# dislocker can handle BitLocker, but Windows 11 uses a newer metadata format
# that dislocker 0.7.3 doesn't support. Expect "Unable to compute regions" error.
# Install: apt install -y dislocker
dislocker -r -V /dev/nbd0p3 -- /mnt/bitlocker  # Will likely fail on Win11

# Disconnect when done
qemu-nbd --disconnect /dev/nbd0
```

**BitLocker on Windows 11 note:** The C: drive uses BitLocker with a virtual TPM (swtpm). The decryption key is released to the booted OS, not to external tools. `dislocker` v0.7.3 does NOT support the latest BitLocker metadata format. The only reliable way to access the decrypted C: drive is:
1. Boot the VM normally (BitLocker auto-unlocks via TPM)
2. Interrupt boot to trigger WinRE (3x power cycle)
3. The Recovery Environment has access to the unencrypted volume

### Screenshot OCR for Blind VM Navigation

Since many models don't have vision, use tesseract to read the VM's display state:

```bash
virsh screenshot windows11 /tmp/screen.png
tesseract /tmp/screen.png stdout --psm 6
# Pin screen: "Enter your PIN"
# Recovery: "Your device ran into a problem"
# Desktop: will show app text/start menu
```

## Multi-Machine Workflow

For RE work specifically, the typical pipeline is:

1. **Linux workstation (lin)** — Download tool installers, crack passwords (SIM format), analyze with Wine where possible, prepare documentation
2. **KVM host (kubuntux)** — Run the Windows VM with KVM acceleration
3. **Windows VM** — Install and run the actual RE tools, capture API traffic, extract files

## BitLocker Recovery via Custom WinRE ISO

When the Windows VM's BitLocker prevents boot or you need filesystem access without the PIN, you can build a bootable WinRE ISO from the VM's own recovery partition — no external Windows ISO download needed.

### Prerequisites

The VM must be destroyed (shut off) and accessible via qemu-nbd:

```bash
# Stop VM and mount its disk
virsh destroy <vm>
modprobe nbd max_part=8
qemu-nbd --connect=/dev/nbd0 /var/lib/libvirt/images/windows11.qcow2

# Mount the recovery partition (usually sda4) — this is the 852MB NTFS partition
mount /dev/nbd0p4 /mnt/recovery

# Mount the EFI partition (usually sda1)
mount /dev/nbd0p1 /mnt/efi
```

### Build the ISO

The three files needed are all present on the VM's own disk:

```bash
mkdir -p /tmp/winpe_iso/{efi/boot,boot,sources}
cp /mnt/efi/EFI/Microsoft/Boot/bootmgfw.efi /tmp/winpe_iso/efi/boot/bootx64.efi
cp /mnt/recovery/Recovery/WindowsRE/boot.sdi /tmp/winpe_iso/boot/
cp /mnt/recovery/Recovery/WindowsRE/Winre.wim /tmp/winpe_iso/sources/boot.wim

# Create UEFI-bootable ISO
genisoimage -o /tmp/winre_boot.iso -V 'WINRE' /tmp/winpe_iso
```

### Boot from the ISO

```bash
# Disconnect qemu-nbd first (VM needs exclusive write lock)
qemu-nbd --disconnect /dev/nbd0

# Modify VM config to boot from ISO
virsh dumpxml <vm> > /tmp/vm_orig.xml  # ⚠️ ALWAYS save original first!
virsh attach-disk <vm> /tmp/winre_boot.iso sdd --type cdrom --mode readonly --config
virsh start <vm>

# Send Shift+F10 after boot for command prompt
sleep 45  # wait for WinRE to load
virsh send-key <vm> KEY_LEFTSHIFT KEY_F10
```

### Auto-launch cmd.exe (avoid blind keyboard injection)

Modify the WinRE.wim's startup config to auto-open a command prompt instead of the GUI:

```bash
# Mount the WIM read-write
wimlib-imagex mountrw /tmp/winpe_iso/sources/boot.wim 1 /tmp/winre_mount --allow-other

# Edit winpeshl.ini to launch cmd.exe instead of recenv.exe
cat > /tmp/winre_mount/Windows/System32/winpeshl.ini << 'EOF'
[LaunchApp]
AppPath=X:\Windows\System32\cmd.exe
EOF

# Unmount (commits changes)
wimlib-imagex unmount /tmp/winre_mount --commit
```

Rebuild and re-attach the ISO. This boots directly into a SYSTEM-level cmd.exe — no SPICE, no keyboard injection needed.

### BitLocker Access from WinRE

Once in the WinRE command prompt:

```cmd
# List volumes (C: may or may not be accessible)
diskpart
list volume
exit

# If BitLocker unlocked via TPM (normal boot was interrupted):
C:
cd Windows\System32

# Utilman swap
ren utilman.exe utilman.exe.bak
copy cmd.exe utilman.exe

# Reboot normally
wpeutil reboot
```

**Important:** If the TPM released the BitLocker key during normal boot (before the boot was interrupted for WinRE), the volume is still accessible from WinRE. If the VM was shut down cleanly and rebooted into WinRE, the TPM key was lost on shutdown and the volume will be locked.

### SPICE Port Discovery

To connect to the VM's display directly when RDP/Tailscale aren't available:

```bash
virsh qemu-monitor-command windows11 --hmp 'info spice'
# Returns: address: 127.0.0.1:5901, auth: none

# Connect directly with SPICE client
spicy -h 127.0.0.1 -p 5901
```

This bypasses all network/firewall issues — SPICE is the VM's native display protocol.

## Clean Install: Utilman Swap Before First Boot (prevents BitLocker lockout)

The safest approach for an RE VM is to do the utilman swap **before Windows boots for the first time**, while the drive is still unencrypted and accessible via qemu-nbd:

```bash
# After Windows install finishes (VM shuts down or reboots)
# Do NOT let it boot into Windows yet

virsh destroy <vm>
modprobe nbd max_part=8
qemu-nbd --connect=/dev/nbd0 /var/lib/libvirt/images/windows11.qcow2

# Identify the Windows partition (usually the largest NTFS)
lsblk /dev/nbd0
# Look for the ~63GB partition

# Mount it
ntfs-3g -o rw /dev/nbd0p3 /mnt/windows 2>/dev/null || \
mount -t ntfs-3g /dev/nbd0p3 /mnt/windows 2>/dev/null || \
echo "Try other partition numbers"

# Do the swap
cd /mnt/windows/Windows/System32
mv utilman.exe utilman.exe.bak
cp cmd.exe utilman.exe
cd /
umount /mnt/windows
qemu-nbd --disconnect /dev/nbd0

# Now boot normally
virsh start <vm>
# At the PIN/login screen, click the Ease of Access icon → SYSTEM cmd prompt
```

**Why before first boot?** Windows 11 enables device encryption automatically during OOBE (Out Of Box Experience). If you complete setup first, BitLocker activates and the offline swap becomes impossible without the recovery key (or the complex WinRE + TPM route).

## ⚠️ CRITICAL: BitLocker + swtpm + `--nvram` = Permanent Lockout

**Never run `virsh undefine --nvram` on a Windows VM with BitLocker + TPM encryption.** Doing so destroys:

1. The **swtpm state** (`tpm2-00.permall`) — the virtual TPM's persistent memory containing the BitLocker key encryption hierarchy
2. The **UEFI NVRAM** (`windows11_VARS.fd`) — boot order, Secure Boot keys, firmware settings

Both are **irrecoverable** — there are no backups. The TPM re-initializes with fresh keys on the next boot. BitLocker detects the TPM mismatch and enters recovery mode, demanding the 48-digit recovery key.

**The only way in after this happens is the BitLocker recovery key**, which was generated during Windows setup and may be:
- Saved to the Microsoft account at https://account.microsoft.com/devices/recoverykey  
- Saved to a local file during setup
- Printed during setup (unlikely for a VM)

**Always** save the original VM XML before making changes:
```bash
virsh dumpxml <vm> > /tmp/<vm>_orig.xml   # ☝️ do this FIRST
# ... edit XML, attach disks, try risky changes ...
# To restore:
virsh destroy <vm>
virsh undefine --nvram   # only do this if you have the backup
virsh define /tmp/<vm>_orig.xml
```

### Memory Dump + dislocker Limitations

`dislocker` v0.7.3 **cannot decrypt modern Windows 11 BitLocker volumes** — even from a memory dump. Key facts:

- The `-f` flag takes a **BEK file** (USB recovery key file), not a raw memory dump
- "Unable to compute regions" = dislocker can't parse the BitLocker metadata format used by Windows 11
- `virsh dump --memory-only` creates an ELF core dump; to convert to raw memory, parse all PT_LOAD segments from ELF headers (requires manual extraction with Python/readelf)
- Even with a raw 4GB memory dump captured while Windows was booted (drive unlocked), dislocker v0.7.3 fails to find the FVEK
- Volatility3 plugins for BitLocker key extraction require the correct Windows profile/symbols, which are often missing for recent builds

**The reliable approaches are:**
1. Boot normally (TPM auto-unlock) → interrupt to WinRE (3x power-cycle) → access decrypted volume
2. Build and boot from a custom WinRE ISO (procedure above)
3. Know the BitLocker recovery key

### Resources VM XML Backup

```bash
# Bare minimum: save the XML before touching the VM
virsh dumpxml <vm> > /tmp/<vm>_$(date +%Y%m%d_%H%M%S).xml
# Also save the swtpm state path for reference
virsh dumpxml <vm> | grep -A5 tpm
```

## Common Pitfalls

- **Missing `<HideOnlineAccountScreens>true</HideOnlineAccountScreens>` in autounattend.xml** — Windows 11 25H2+ ignores `<SkipMachineOOBE>` and `<SkipUserOOBE>` if a network connection is present. You MUST include `<HideOnlineAccountScreens>true</HideOnlineAccountScreens>` in the `<OOBE>` section, otherwise setup forces a Microsoft account sign-in even with a full answer file. This is the single most common cause of a \"working\" autounattend.xml that still prompts for a login.

- **Verifying ISO UEFI boot support** — Use Python to check the El Torito boot catalog. Entry type `0x88` = x86 BIOS, type `0x91` = EFI:
  ```bash
  python3 -c '
  import struct
  with open("/path/to/file.iso","rb") as f:
      for s in range(16,50):
          f.seek(s*2048); vd=f.read(7)
          if vd[0]==0 and vd[1:6]==b"EL TORITO SPECIFICATION":
              bc=struct.unpack("<I",vd[6:10])[0]; break
      f.seek(bc*2048); cat=f.read(256)
      for i in range(0,256,32):
          if cat[i] in (0x88, 0x91):
              arch={0:"x86",0xEF:"EFI"}.get(cat[i+1],hex(cat[i+1]))
              print(f"{arch} boot " + ("(EFI)" if cat[i+1]==0xEF else ""))
  '
  ```
  If only `x86` entries appear and no `EFI` (0xEF platform) entry, the ISO lacks UEFI El Torito support. The `isoinfo -d -i file.iso` command only shows the default (x86) entry — it does NOT list alt-boot entries.

- **SeaBIOS + i440fx as diagnostic fallback** — When OVMF reports \"No bootable option or device was found\" and you can't figure out why, switch to i440fx + SeaBIOS (BIOS mode) as a diagnostic step. If the ISO boots under SeaBIOS but not OVMF, the issue is UEFI-specific (bad El Torito EFI entry, missing GPT partition, Secure Boot). If it doesn't boot under either, the ISO itself is broken. Note: Windows 11 setup will refuse to install under BIOS/CSM — this is purely a diagnostic path to confirm the ISO is functional.

- **Checking multiple ISO storage locations** — Official ISOs may have been downloaded previously. Check these in order:
  ```bash
  find /mnt/storage -name '*.iso' -size +1G -type f 2>/dev/null
  find /var/lib/libvirt/images -name '*.iso' -size +1G 2>/dev/null
  find /home -name '*.iso' -size +1G -type f 2>/dev/null
  ```
  On kubuntux specifically, old VMs and ISOs are often at `/mnt/storage/VMs/` which has `images/` and `iso/` subdirectories.

- **genisoimage UEFI boot is broken** — genisoimage's `-eltorito-alt-boot -e` copies the efisys.bin file into the ISO but does NOT register it as a valid EFI boot entry in the El Torito catalog. OVMF reports "No bootable option or device was found". Use **xorriso** with `-isohybrid-gpt-basdat` instead. See `references/uup-autounattend-workflow.md` for the exact command.
- **grep is case-sensitive on ISO filenames** — ISO9660 filenames are uppercase by convention (EFISYS.BIN). `grep efisys` finds nothing; `grep -i efisys` finds it. Don't conclude "the ISO doesn't have UEFI boot files" from a case-sensitive grep miss.

- **Wine can't handle SIM installers** — Smart Install Maker's file copy code fails in Wine. Don't waste time trying — use a real Windows VM.
- **SATA hotplug not supported** — Can't attach CDROMs or disks to a running VM via SATA bus. Shut it down first.
- **Duplicate MAC addresses break Windows networking** — Windows sees two NICs with the same MAC as one device.
- **virsh send-key is unreliable** — Works for simple password entry but fails on UI wizards, UAC prompts, and installer dialogs. Prefer RDP/Tailscale.
- **Admin cmd via keyboard injection DOES NOT WORK** — `Win+R → cmd → Ctrl+Shift+Enter` fails because UAC elevation steals focus and the subsequent key presses don't reach the admin console. Text ends up in Start menu search or whatever window regains focus instead. For admin commands that require UAC, use SPICE/virt-viewer. Don't burn time trying to script this — it's a known dead end.
- **Windows Firewall blocks everything inbound** — Including ping, RDP, and SMB. Must be disabled or configured via local admin.
- **RDP not available at lock screen** — The Windows RDP service starts AFTER user logs in to the desktop. If the VM is at the PIN/password screen, RDP port 3389 will be closed even though Tailscale is connected and pings succeed. Log in via SPICE/virt-viewer first, then RDP works.
- **Use SPICE when RDP isn't set up yet** — If RDP was never enabled on the VM (fresh install or it was disabled), keyboard injection can't fix it. Have the user run `remote-viewer spice://127.0.0.1:<port>` or `virt-viewer <vm>` to connect directly, then enable RDP manually. This is a one-time setup — once enabled, RDP survives reboots.
- **VM overprovisioning kills the host** — Never allocate more than 40% of host RAM to a single VM. A 10GB VM on a 16GB host leaves ~2GB for the OS + Chrome + everything else, forcing heavy swap. On the Skylake i7-6700 (4C/8T), cap VM at 2-4 vCPUs and 4-6GB RAM for RE tool workloads. Shrink with `virsh edit <vm>` (requires shutdown + restart). See `references/resource-sizing.md`.
- **`remote-viewer` SPICE protocol error** — `remote-viewer spice://127.0.0.1:PORT` can fail with "the SPICE protocol is not installed" even when all SPICE libraries are present. This is a desktop-environment URI handler registration issue, not a missing package. Use `spicy -h 127.0.0.1 -p PORT` instead — it's a dedicated SPICE client that always works.
- **Q35 SATA controller** — The q35 chipset does NOT auto-add a SATA controller. You must explicitly define one with the correct PCI address, or OVMF won't detect SATA-attached CDROMs/disks and will report "No bootable option or device was found". Add to the VM XML:
  ```xml
  <controller type='sata' index='0'>
    <address type='pci' domain='0x0000' bus='0x00' slot='0x1f' function='0x2'/>
  </controller>
  ```
  All disk devices must use `bus='sata'` (not `bus='ide'`). The IDE bus is not fully wired on q35 and OVMF can't boot from it.
