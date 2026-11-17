# UUP → Unattended Windows ISO — Full Chain

## Overview

Take a UUP dump download through to a bootable Windows 11 ISO with embedded
autounattend.xml for fully automated install. Produces a VM with user RE /
pass re123, no BitLocker, no OOBE prompts.

## Step-by-step

### 1. Download UUP files

Use uupdump.net → "Latest Public Release build" → x64 → English (US) →
editions: Home + Pro. Select **"Download UUP set"** (NOT "Download and
convert to ISO" — that requires Windows). The resulting ZIP contains:

- `uup_download_linux.sh`  — aria2-based downloader
- `files/get_aria2.ps1`    — PowerShell fallback
- `readme.unix.md`         — instructions

### 2. Download & convert

```bash
unzip 26200.*.zip -d /tmp/windows-iso
cd /tmp/windows-iso
chmod +x *.sh
./uup_download_linux.sh    # ~10GB via aria2

# After download, convert using uup-converter
git clone https://git.uupdump.net/uup-dump/converter.git /tmp/uup-converter
cd /tmp/uup-converter
bash convert.sh wim /tmp/windows-iso/UUPs/ 0
```

Output ISO appears in converter dir as `*.ISO` (~4.1GB). The converter
produces a hybrid ISO with both BIOS (etfsboot.com) and UEFI
(efi/microsoft/boot/efisys.bin) boot files.

**⚠️ Verify the ISO has UEFI boot support:**

```bash
# Check efisys.bin exists (CASE-SENSITIVE filesystem in ISO9660!)
isoinfo -f -i /path/to/*.ISO | grep -i efisys
# Should return: /EFI/MICROSOFT/BOOT/EFISYS.BIN

# Check the El Torito boot catalog for EFI entries:
python3 -c "
with open('/path/to/*.ISO','rb') as f:
    import struct
    # Find boot catalog sector
    for s in range(16,50):
        f.seek(s*2048)
        vd=f.read(7)
        if vd[0]==0 and vd[1:6]==b'EL TORITO SPECIFICATION':
            bc=struct.unpack('<I',vd[6:10])[0]; break
    f.seek(bc*2048); cat=f.read(256)
    for i in range(0,256,32):
        if cat[i]==0x88:
            arch={0:'x86',1:'PPC',0xEF:'EFI'}.get(cat[i+1],hex(cat[i+1]))
            media={0:'NoEmul',1:'1.2M',2:'1.44M',4:'HDD'}.get(cat[i+2],hex(cat[i+2]))
            print(f'  {arch} {media}')
"
# If only 'x86 NoEmul' appears, there's NO UEFI El Torito entry.
# This is OK if xorriso was used with -isohybrid-gpt-basdat (see below).
```

### 3. Inject autounattend.xml into boot.wim

The converter output has a `sources/boot.wim` with 2 images:
- Index 1: Windows PE
- Index 2: Windows Setup (modify this one)

```bash
mkdir -p /tmp/iso_mount /tmp/iso_edit
mount -o loop /tmp/uup-converter/*.ISO /tmp/iso_mount
rsync -a /tmp/iso_mount/ /tmp/iso_edit/
umount /tmp/iso_mount

# Copy boot.wim to writable location
cp /tmp/iso_edit/sources/boot.wim /tmp/boot.wim

# Mount index 2 (Windows Setup) read-write
wimlib-imagex mountrw /tmp/boot.wim 2 /tmp/wim_mount --allow-other

# Copy autounattend.xml to WIM root AND Sysprep dir
cp autounattend.xml /tmp/wim_mount/
mkdir -p /tmp/wim_mount/Windows/System32/Sysprep
cp autounattend.xml /tmp/wim_mount/Windows/System32/Sysprep/

# Commit changes and replace boot.wim
wimlib-imagex unmount /tmp/wim_mount --commit
cp /tmp/boot.wim /tmp/iso_edit/sources/boot.wim
```

### 4. Repack ISO — ⚠️ USE XORRISO, NOT GENISOIMAGE

**genisoimage is broken for UEFI boot**: even with `-eltorito-alt-boot -e ...`,
it copies the efisys.bin file into the ISO but does NOT create a valid
El Torito EFI boot entry in the boot catalog. OVMF sees "x86" entries only
and reports "No bootable option or device was found."

**xorriso** with `-isohybrid-gpt-basdat` creates a hybrid MBR+GPT disk image
that UEFI can discover via the GPT partition table, bypassing the broken
El Torito EFI entry entirely:

```bash
cd /tmp/iso_edit
xorriso -as mkisofs \
  -isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
  -b boot/etfsboot.com -no-emul-boot -boot-load-size 8 \
  -eltorito-alt-boot -e efi/microsoft/boot/efisys.bin -no-emul-boot \
  -isohybrid-gpt-basdat \
  -V 'Win11_RE' \
  -o /var/lib/libvirt/images/Win11_unattended.iso \
  .
```

**Key parameters explained:**
| Flag | Purpose |
|------|---------|
| `-isohybrid-mbr` | Write BIOS boot code to the MBR (allows BIOS boot) |
| `-b etfsboot.com` | BIOS El Torito boot image (x86) |
| `-eltorito-alt-boot -e efisys.bin` | EFI boot image — but xorriso still doesn't write the EFI El Torito entry correctly to the catalog for all firmware |
| `-isohybrid-gpt-basdat` | Create GPT partition with the boot data — this is what makes UEFI boot WORK. Without this, OVMF can't find a UEFI boot path. |

**xorriso creates `-isohybrid-gpt-basdat` without asking for extra packages** —
the `isohdpfx.bin` comes from the `isolinux` package.

**Takes ~2 min** (xorriso is ~5x faster than genisoimage for 4GB).

### 5. Verify the output ISO has UEFI boot capability

```bash
# Check the GPT partition table contains the EFI boot partition
xorriso -toc /var/lib/libvirt/images/Win11_unattended.iso 2>&1 | grep -i efi
# Or check via hex:
python3 -c "
with open('/var/lib/libvirt/images/Win11_unattended.iso','rb') as f:
    # Check for GPT signature at LBA 1
    f.seek(512)
    sig = f.read(8)
    print('GPT present:', sig == b'EFI PART')
    # Count El Torito entries
    for s in range(16,50):
        f.seek(s*2048)
        vd=f.read(7)
        if vd[0]==0 and vd[1:6]==b'EL TORITO SPECIFICATION':
            bc=struct.unpack('<I',vd[6:10])[0]; break
    f.seek(bc*2048); cat=f.read(256)
    for i in range(0,256,32):
        if cat[i]==0x88:
            arch={0:'x86',0xEF:'EFI'}.get(cat[i+1],hex(cat[i+1]))
            print(f'  {arch} boot entry')
"
```

If you see "GPT present: True" and at least one boot entry, the ISO should
boot under OVMF.

### 6. Define & start VM — ⚠️ UUP converter ISO is known to fail in KVM

The UUP converter on Linux (genisoimage or xorriso) produces ISOs that do NOT reliably boot in KVM, regardless of configuration. Known failed attempts:

| Machine Type | Firmware | Disk Bus | Outcome |
|-------------|----------|----------|---------|
| q35 (OVMF) | UEFI + Secure Boot | SATA | "No bootable option" |
| q35 (OVMF) | UEFI, no Secure Boot | SATA | "No bootable option" |
| q35 (OVMF) | UEFI + genisoimage | SATA | "No bootable option" |
| q35 (OVMF) | UEFI + xorriso + isohybrid | SATA | "No bootable option" |
| i440fx (SeaBIOS) | BIOS | SATA | 328KB disk, no boot |
| i440fx (SeaBIOS) | BIOS | IDE | 200KB disk, no boot |
| i440fx (SeaBIOS) | BIOS | virtio | 200KB disk, no boot |
| virt-install auto | UEFI | SATA | 200KB disk, no boot |

The converter ISOs lack proper UEFI boot entries in the El Torito catalog. The efisys.bin is present in the ISO but is never registered with platform ID 0xEF. Even xorriso's `-isohybrid-gpt-basdat` option (which creates a GPT partition for the EFI data) does not reliably make OVMF recognize the ISO as bootable.

**If you need a working Windows VM in KVM, DO NOT use the UUP converter. Use an official Microsoft ISO.**

**Critical q35 SATA controller** (missing this = "No bootable option"):
```xml
<controller type='sata' index='0'>
  <address type='pci' domain='0x0000' bus='0x00' slot='0x1f' function='0x2'/>
</controller>
```

**Do NOT use `bus='ide'` on q35** — the IDE bus is not fully wired and OVMF
can't boot from it. All disks must use `bus='sata'`.

The autounattend creates user **RE** / **re123**, skips all OOBE, and
disables BitLocker by using a local account.

### 7. Utilman swap before first boot (prevents BitLocker lockout)

Windows 11 enables device encryption automatically during OOBE. After
autounattend completes the first boot, BitLocker kicks in. Do the swap
IMMEDIATELY after install before Windows boots:

```bash
virsh destroy windows11
modprobe nbd max_part=8
qemu-nbd --connect=/dev/nbd0 /var/lib/libvirt/images/win11.qcow2

# Identify Windows partition — usually the largest NTFS
lsblk /dev/nbd0
# Mount it (try p3, p4, etc.)
ntfs-3g -o rw /dev/nbd0p3 /mnt/windows

cd /mnt/windows/Windows/System32
mv utilman.exe utilman.exe.bak
cp cmd.exe utilman.exe
cd /
umount /mnt/windows
qemu-nbd --disconnect /dev/nbd0

virsh start windows11
# At login screen → click Ease of Access icon → SYSTEM cmd prompt
```

## Pitfalls

### genisoimage UEFI boot is broken

genisoimage's `-eltorito-alt-boot -e` copies the EFI boot image into the ISO
but does NOT register it in the El Torito boot catalog with the correct EFI
platform ID (0xEF). The catalog only contains x86 (0x00) entries. OVMF
reports "No bootable option or device was found" even though efisys.bin
exists in the ISO.

**Always use xorriso for UEFI-bootable Windows ISOs on Linux.**

### Case-sensitivity when probing ISO contents

ISO9660 filenames are case-insensitive at the filesystem level but `grep`
(default) is not. When checking for efisys.bin:

```bash
# WRONG — misses EFISYS.BIN
isoinfo -f -i file.iso | grep efisys

# CORRECT
isoinfo -f -i file.iso | grep -i efisys
```

The UUP converter DOES produce an efi directory with the correct boot files.
If grep says "no efisys", you likely forgot `-i`.

### xorriso vs genisoimage speed

| Tool | 4GB ISO build time |
|------|-------------------|
| genisoimage | ~10 minutes |
| xorriso | ~2 minutes |

### Image index for consumer multi-edition ISOs

```
Index 1 = Windows Home
Index 5 = Windows Pro N
Index 6 = Windows Pro (use this for RE work)
```

### Windows 11 requires UEFI for install

Even with a BIOS-bootable setup disc, Windows 11 setup checks for UEFI
firmware and refuses to install if it's not present. SeaBIOS/CSM boot
won't work — you MUST use OVMF UEFI firmware.

### `grep -v UPDATE` breaks xorriso

Piping xorriso's output through `tail` or `grep` can cause it to write to
stdout instead of the output file. Let it run without pipe filtering, or
use `grep -v` sparingly. Better: redirect to a log file and tail that.

## Sample autounattend.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
    <settings pass="windowsPE">
        <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
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
        <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
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
            </OOBE>
        </component>
    </settings>
</unattend>
```

## Verifying autounattend.xml was picked up

After the VM boots for the first time, check that the install was automated:
- The VM should NOT show a language/country selection screen
- It should NOT ask for a Microsoft account
- It should boot directly to the desktop with user RE logged in
- If you see "Hi, let's get started" or Cortana, the autounattend was NOT
  found by Windows Setup
