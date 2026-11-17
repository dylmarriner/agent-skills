# Windows VM RE Workflow — kubuntux

QEMU/KVM Windows 11 VM on kubuntux used for dynamic analysis of commercial phone unlocking tools (Octoplus, Medusa, Chimera, etc.).

## VM Setup

| Property | Value |
|----------|-------|
| **Host** | kubuntux (100.93.75.87) |
| **VM name** | `windows11` |
| **Disk** | `/var/lib/libvirt/images/windows11.qcow2` (64G) |
| **RAM** | 4 GB |
| **CPU** | 2 cores |
| **Graphics** | SPICE on localhost:5901 (no auth) |
| **NICs** | 2x default libvirt network (192.168.122.14) |
| **C: drive** | BitLocker encrypted (/dev/sda3, 63G) |
| **Recovery** | /dev/sda4 (NTFS, 852M) |
| **EFI** | /dev/sda1 (vfat, 200M) |
| **Login** | Windows Hello PIN |

## Samba Share for File Transfer

The RE folder is shared from the host to the VM:

```bash
# Already configured in /etc/samba/smb.conf:
[RE]
   path = /home/kubuntux/Downloads/RE
   browseable = yes
   read only = no
   guest ok = yes
   force user = kubuntux
```

Accessible from the VM at `\\192.168.122.1\RE`.

## VM Automation via libvirt (virsh)

### Taking Screenshots (the only way to see VM state non-interactively)

```bash
virsh screenshot windows11 /tmp/vm_screenshot.ppm
# Output is PNG despite .ppm extension
scp root@100.93.75.87:/tmp/vm_screenshot.ppm ./
tesseract ./vm_screenshot.png stdout --psm 6  # OCR for text extraction
```

### Sending Keyboard Input

Uses Linux keycode names (not scancodes):

```bash
# Win+R (open Run dialog)
virsh send-key windows11 --codeset linux KEY_LEFTMETA KEY_R

# Type a path (max ~8-10 keys per command, split if needed)
virsh send-key windows11 --codeset linux KEY_BACKSLASH KEY_BACKSLASH KEY_1 KEY_9 KEY_2

# Enter
virsh send-key windows11 --codeset linux KEY_ENTER
```

**Limitations:**
- Max ~8-10 keycodes per `send-key` command
- Key events go to whichever window has focus (login screen, desktop, etc.)
- NZ/US keyboard layout differences matter for special characters

### Power Cycling to Trigger Recovery

Windows boot failure detection: 3 consecutive interrupted boots → Automatic Repair → Recovery Environment.

```bash
for i in 1 2 3; do
  sleep 15
  virsh reset windows11
done
# Next boot shows: "Your device ran into a problem... Click Enter to see recovery options"
```

### Navigating Windows Recovery Environment (WinRE)

From the recovery screen, navigate to Troubleshoot → Advanced Options → Command Prompt:

| Screen | Action |
|--------|--------|
| "Your device ran into a problem..." | Press Enter |
| "Choose an option" | Tab×3 → Enter (select Troubleshoot) |
| Troubleshoot menu | Tab → Enter (select Advanced Options) |
| Advanced Options | Tab → Enter (select Command Prompt) |

### utilman.exe / Sticky Keys Trick

Replace utilman.exe with cmd.exe from WinRE so clicking Ease of Access at the PIN screen launches a SYSTEM shell. The C: drive is BitLocker-unlocked after TPM auto-unlock during boot, so it's accessible from WinRE.

```cmd
C:
cd Windows\System32
ren utilman.exe utilman.exe.bak
copy cmd.exe utilman.exe
exit
```

Reboot → at PIN screen, click Ease of Access icon → cmd.exe as SYSTEM. Then:
```cmd
net user Administrator /active:yes
net user Administrator Password123
```

### Clean Shutdown

```bash
# When done with guestmount/nbd:
guestunmount /mnt/win-vm
qemu-nbd --disconnect /dev/nbd0
virsh start windows11
```

## Raw Disk Access (nbd)

When the VM is shut off, mount the qcow2 directly:

```bash
virsh destroy windows11
modprobe nbd max_part=8
qemu-nbd --connect=/dev/nbd0 /var/lib/libvirt/images/windows11.qcow2
lsblk /dev/nbd0
# Partitions: nbd0p1 (EFI), nbd0p2 (MSR), nbd0p3 (C: - BitLocker), nbd0p4 (Recovery - NTFS)
```

## BitLocker

**Windows 11 BitLocker is NOT supported by `dislocker 0.7.3`** — it crashes with the newer metadata format. The C: drive (nbd0p3) decrypts via TPM during normal boot — from the host side it's unreadable. The recovery partition (nbd0p4, NTFS) is NOT encrypted and mounts fine with guestmount.

Normal boot (TPM auto-unlock) → WinRE → utilman trick is the working path to get a SYSTEM shell.

## What's in the RE Folder

Path: `/home/kubuntux/Downloads/RE/` (5.4GB total)

### Extracted/Reported Tools
| Tool | Packer | Status |
|------|--------|--------|
| Octoplus Samsung 5.1.2.2 | UPX + TeK | ✅ Reported |
| Octoplus FRP 3.0.6.0 | TeK + LAx | ✅ MetaCore patched, DLM patched |
| Octoplus JTAG 1.9.5.6 | VMProtect 2.x | ✅ Reported |
| Octoplus PRO JTAG 2.2.5.7 | K9/Korimir | ✅ Reported |
| Medusa Pro 2.2.5.8 | K9/Korimir | ✅ Reported |
| Medusa Flasher 1.1.0.2 | VMProtect | ✅ Reported |
| Octoplus Suite 1.6.7 | VMProtect/Themida | ✅ Reported |
| ChimeraInstaller.exe | Winlice | ✅ Boot sections extracted |
| Apizu V4.4.4 | SIM installer | pw:1234, blocked |
| Hydra V7.0 | SIM installer | pw:hydratool, blocked |

### Results in `~/Downloads/RE/results/`
- jtag_1956_report.md — Octoplus JTAG analysis
- jtag_pro_2257_report.md — Octoplus PRO JTAG analysis  
- medusa_pro_2258_report.md — Medusa Pro analysis
- medusa_flasher_1102_report.md — Medusa Flasher analysis
- suite_167_report.md — Octoplus Suite analysis
- decompressed_*.bin — TeK stub decompression fragments
- frp_unlock_methods.md — FRP method research
- octoplus_backdoor_plan.md — License bypass plan
- octoplus_re_report.md — Octoplus Samsung RE report
