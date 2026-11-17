---
name: kvm-windows-vm
description: KVM Windows VM for RE, UUP ISO download and utilman swap.
---

# KVM Windows VM for RE Work

## When to use
Setting up or reinstalling a Windows VM on KVM/libvirt for RE tools (Octoplus, Chimera, Medusa). Not for general Windows VM use.

## Phase 1: Get the Windows ISO

### Via UUP dump (reliable, no captcha)

1. Browse to uupdump.net → "Latest Public Release build" → x64
2. Select build (e.g. 26200.8968 amd64)
3. Language: English (United States)
4. Edition: Windows Home + Windows Pro → Next
5. Select "Download UUP set" (not "ISO" — that needs Windows)
6. Click "Create download package" — downloads .zip
7. Extract, run `bash uup_download_linux.sh` — ~10GB via aria2
8. Convert: clone the converter and run `bash convert.sh wim UUPs/ 0`

### Massgrave (has Cloudflare) — avoid

## Phase 2: Create VM

```bash
qemu-img create -f qcow2 disk.qcow2 68G
# Define with: UEFI+OVMF, swtpm, 4GB RAM, 2 vCPU, SPICE
# Attach ISO as SATA CD-ROM
```

**CRITICAL:** Prevent BitLocker — use LOCAL account during install, not Microsoft. Or use IoT Enterprise.

## Phase 3: Utilman swap (before first login)

```bash
# VM OFF
guestmount -a disk.qcow2 -m /dev/sda3 /mnt/win
# If FVE-FS- marker = BitLocker, use dislocker
mv /mnt/win/Windows/System32/utilman.exe{,.bak}
cp /mnt/win/Windows/System32/cmd.exe /mnt/win/Windows/System32/utilman.exe
guestunmount /mnt/win
```

At login screen: Win+U → SYSTEM cmd → `net user Administrator /active:yes`

## Phase 4: RE tool setup

1. Disable Defender via Group Policy
2. Install virtio drivers
3. SMB share: `\\192.168.122.1\RE`
4. Deploy DLL interposers (libusb, WinSCard) for USB protocol capture

## Pitfalls

- BitLocker auto-enables with Microsoft account — use LOCAL
- `virsh undefine --nvram` destroys TPM — NEVER do this
- qemu-nbd holds write lock — disconnect before starting VM
- zerofs.link blocked by Cloudflare — use UUP dump
