# Samsung IMEI Change — Methods & Tools

Class of work: modifying the IMEI (International Mobile Equipment Identity) of a Samsung device for legitimate repair purposes.

## Device: SM-A546E (Exynos 1380)

IMEI is stored in:
- `/efs/imei/imei.txt` (readable with root)
- `/efs/nv_data.bin` or partition-based NV storage (Exynos modem firmware)
- Modem partitions: `m9kefs1`, `m9kefs2` on Exynos 1380

## Methods (ordered by reliability)

### 1. Octoplus Samsung Tool (v5.1.2.2+)

The most comprehensive Windows-based Samsung tool. Supports Exynos 1380 IMEI write directly.

- **Install:** `install_octoplus_samsung_5.1.2.2.exe` (extracted on kubuntux)
- **Requires:** Windows VM + hardware dongle or server credits
- **Available on kubuntux:** `/home/kubuntux/Downloads/RE/install_octoplus_samsung_5.1.2.2.exe`

### 2. Chimera Tool

Czech-based Samsung/Mediatek tool. IMEI via server credits (no dongle).

- **Status:** Extracted on kubuntux, Winlice-packed
- **Requires:** Windows VM + server credits (gsmserver.com account)

### 3. Z3X Samsung Tool Pro

Major Samsung service tool. Same dongle/server model as Octoplus.

### 4. Engineering Bootloader + AT Commands

Flash a signed engineering bootloader, then:

```
AT+EGMR=1,7,"NEW_IMEI"
```

- **Risk:** Samsung Knox blocks eng bootloaders on newer firmware
- **Requires:** Model/firmware-specific eng bootloader for A546E

### 5. Root + EFS Direct

Root with Magisk, then modify directly:

```bash
# Backup first!
dd if=/dev/block/by-name/efs of=/sdcard/efs_backup.img

# Find modem partitions (Exynos 1380: m9kefs1, m9kefs2)
ls -la /dev/block/platform/13500000.dwmmc0/by-name/ | grep -i efs

# Dump, hex-edit IMEI, write back
dd if=/dev/block/by-name/m9kefs1 of=/sdcard/dump.bin
# edit dump.bin (IMEI in ASCII at known offsets)
dd if=/sdcard/dump_modified.bin of=/dev/block/by-name/m9kefs1
```

- **Requires:** Root (Magisk)
- **Risk:** Incorrect write can brick the modem permanently

### 6. AT Command via USB (standard boot)

The riskeco AT method switches USB to modem mode exposing CDC ACM serial. Once connected:

```
AT+CGSN   # Query IMEI
AT+EGMR=1,7,"NEW_IMEI"  # Usually locked without eng bootloader
```

## Windows VM Dependency

All Windows-based tools need the VM. See `windows-re-vm-setup` skill for VM status. Until the VM is running, only root+EFS or eng bootloader paths are viable.
