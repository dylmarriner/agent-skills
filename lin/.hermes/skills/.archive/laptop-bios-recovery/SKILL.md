---
name: laptop-bios-recovery
description: >-
  Recover or clear BIOS/UEFI admin passwords on consumer laptops (HP, Dell,
  Lenovo, Acer, Asus) using software methods — kernel modules, ACPI/WMI
  manipulation, setup variable modification, service tag master passwords,
  and CMOS clear techniques. Covers machines where the password locks BIOS
  setup but the OS still boots.
category: security
---

# Laptop BIOS/UEFI Password Recovery

Class-level skill for bypassing or clearing BIOS admin passwords on consumer
laptops. Focus is on **software methods** — hardware desoldering/external SPI
flash programming is out of scope.

## Trigger Conditions

- User says "BIOS locked", "BIOS password", "admin password on laptop", "forgot BIOS password"
- User reports laptop boots to OS fine but can't enter BIOS setup
- User mentions HP Pavilion, ProBook, EliteBook, Dell Latitude, Lenovo ThinkPad
- User can run commands from the OS (Linux/Windows) but can't change BIOS settings

## General Methodology

### Phase 1: Assess the Situation

1. **Can the OS boot?** If yes → software methods are viable (highest chance)
2. **What BIOS vendor?** Identify via `dmidecode -t bios` (Insyde H2O, AMI Aptio, Phoenix, etc.)
3. **What laptop brand?** Each has different approaches — HP has the richest software attack surface
4. **Is Secure Boot on?** Check with `mokutil --sb-state`
5. **Is the password set on UEFI Setup variables?** Most modern laptops store it in NVRAM, not CMOS

### Phase 2: OS-Level Reconnaissance

```bash
# Get BIOS info
sudo dmidecode -t bios

# Check if WMI interface exists (HP-specific)
ls /sys/bus/wmi/drivers/hp-wmi/

# Check for ACPI methods
sudo cat /sys/firmware/acpi/tables/DSDT > /tmp/dsdt.dat

# Check for hp-bioscfg kernel module
modinfo hp-bioscfg 2>/dev/null && echo "AVAILABLE" || echo "NOT AVAILABLE"

# Check EFI variables
ls /sys/firmware/efi/efivars/ 2>/dev/null | head -20
```

### Phase 3: Try Software Routes (in order)

#### Method A: hp-bioscfg kernel module (HP only)

The `hp-bioscfg` kernel module exposes BIOS configuration settings via
`/sys/devices/platform/hp-bioscfg/`. When loaded, it provides read/write access
to individual BIOS settings including the admin password.

```bash
# Load the module
sudo modprobe hp-bioscfg

# Check what's exposed
ls /sys/devices/platform/hp-bioscfg/
ls /sys/devices/platform/hp-bioscfg/admin_password/

# The admin_password interface usually has:
#   - current_value  (read current password status)
#   - is_enabled     (is a password set?)
#   - set_password   (write to change/clear)
```

**If hp-bioscfg doesn't exist** (not built or older kernel), it may need
building from the hp-bioscfg source against your running kernel. You can
also check:

```bash
# Alternative: check if HP WMI exposes it
ls /sys/bus/wmi/devices/*HP*/ 2>/dev/null
```

#### Method B: WMI ACPI Interface (HP, some Dell)

HP laptops expose a WMI GUID (`05901221-D566-11D1-B2F0-00A0C9062910`) that
provides BIOS configuration access via ACPI methods. This is the same
interface `hp-bioscfg` uses under the hood.

```bash
# Check if the WMI device exists
# Look in /sys/bus/wmi/devices/ or /dev/wmi/
# Try reading the WMI data block
```

**If WMI shows the password byte in the ACPI Setup variable table,**
you can locate the specific NVRAM variable that controls the admin password
flag and write a 0x00 to clear it. This requires:
1. Dumping the ACPI tables
2. Finding the Setup variable table in NVRAM
3. Identifying which byte position controls the admin password
4. Writing 0x00 to that position

#### Method C: setup_var / setup_var2 (UEFI Setup variable manipulation)

For Insyde H2O and AMI Aptio BIOS, the `setup_var` tool can read/write UEFI
Setup variables in NVRAM. These tools run from a UEFI shell (not from the OS).

```bash
# From UEFI shell:
setup_var 0xXXXX          # Read a setup variable
setup_var 0xXXXX 0x00     # Write 0x00 to clear password
```

**The challenge:** finding the right offset. The admin password flag is at
different offsets on every BIOS version. Sources:
- Extract from a known-good BIOS dump of the exact same model + BIOS version
- Brute-force scan (time-consuming)
- Use ACPI Setup variable table from DSDT to locate the variable

#### Method D: Service Tag / Master Password (Dell, HP old models)

**Dell:** Master password is derived from the service tag using a known
algorithm. Online calculators or hashcat can generate:

```bash
# Get service tag
sudo dmidecode -t system | grep "Serial Number"

# Common patterns for Dell:
#   - Older models: service tag + known prefix
#   - Newer models: hashcat mode 13800 (Dell BIOS)
```

**HP older models:** Some older HP models (pre-2018) have backdoor master
passwords. Generation depends on service tag and model series.

**HP modern models (Pavilion 15-cs0xxx confirmed): DO NOT display an unlock
code on screen after 3 failed BIOS password attempts.** Without this code,
bios-pw.org and similar generators are dead ends — they require the on-screen
code, not the serial number. If no code appears after 3 failed attempts, skip
directly to Method G (efivar nuke) or Method H (SPI flash).

#### Method E: CMOS Clear

**Works on:** older laptops (pre-2015), some modern ones with removable CMOS
battery. UEFI NVRAM passwords on modern laptops are NOT cleared by CMOS reset.

```bash
# Steps:
# 1. Power off, unplug AC
# 2. Remove main battery (if removable)
# 3. Remove CMOS coin cell (CR2032)
# 4. Hold power button 30s to discharge caps
# 5. Wait 5+ minutes
# 6. Reinsert CMOS battery, power on
# 7. If NVRAM was cleared, enter BIOS — password should be gone
```

#### Method F: BIOS Flash / Recovery (before hardware)

Flashing a known-good BIOS from the vendor (BIOS recovery mode):

```bash
# HP: Windows key + B at power-on
# Dell: Ctrl + Esc at power-on
# Lenovo: Fn + R at power-on

# This reflashes the entire BIOS, replacing the NVRAM and password.
# Works on most models. Requires vendor BIOS image on FAT32 USB.
```

#### Method G: Linux efivar Direct Manipulation (Insyde H2O / AMI)

On HP Pavilions and other modern laptops running Linux, the admin password is
stored in a UEFI NVRAM variable visible under `/sys/firmware/efi/efivars/`.
This is the **cleanest software method** — no UEFI shell, no kernel module
building, no ACPI reverse engineering.

**The target variables:**

| Variable | Contents | Size | Immutable? |
|----------|----------|------|------------|
| `Setup-{GUID}` | Full BIOS setup config including password bytes | 1.8K+ | Yes |
| `HPMS-30fef3a5-ba29-4767-9f11-7c7fd606ffa6` | HP-specific password store (5 bytes: 4 header + 1 data) | 5 bytes | Yes |
| `H19SetupVariable-30fef3a5-ba29-4767-9f11-7c7fd606ffa6` | BIOS-revision + service-tag data | 21 bytes | No (may be writeable without chattr) |

**The GUID for HP systems using Insyde H2O:**
- Setup: `a04a27f4-df00-4d42-b552-39511302113d`
- HPMS & H19SetupVariable: `30fef3a5-ba29-4767-9f11-7c7fd606ffa6` (same GUID, different variable names)
- Check yours with: `ls /sys/firmware/efi/efivars/ | grep -iE '(Setup|HPMS)'`

**Procedure:**

```bash
# 1. IDENTIFY the variables
ls /sys/firmware/efi/efivars/ | grep -iE '(Setup|HPMS)'
lsattr /sys/firmware/efi/efivars/ | grep -iE '(Setup|HPMS)'
# The Setup variable will show ----i----------------- (immutable)

# 2. BACKUP (IMPORTANT: use cat, NOT dd or cp)
# dd and cp use lseek which FAILS on efivars
mkdir -p ~/bios_backup
cat /sys/firmware/efi/efivars/Setup-{GUID} > ~/bios_backup/Setup.bin
cat /sys/firmware/efi/efivars/HPMS-{GUID} > ~/bios_backup/HPMS.bin

# 3. REMOVE IMMUTABLE FLAG
sudo chattr -i /sys/firmware/efi/efivars/Setup-{GUID}
sudo chattr -i /sys/firmware/efi/efivars/HPMS-{GUID}

# 4. ANALYZE the variable data
# EFI variable format: 4 bytes UEFI attrs header, then data
# The password bytes are at model-specific offsets in the data portion
xxd ~/bios_backup/Setup.bin | head -40
# Look for non-zero bytes in the settings area — typically a single byte
# that's 0x01 when password is set, should be 0x00 when clear

# 5. ZERO the password bytes
# Write a minimal equivalent with password bytes zeroed
# OR (nuclear — zeros the whole Setup variable, may reset all BIOS settings):
printf '\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00...' > /sys/firmware/efi/efivars/Setup-{GUID}
# SAFER: create replacement file with same size but password bytes zeroed

# 6. REBOOT and enter BIOS
sudo reboot
# Password should be gone
```

**The 4-byte UEFI attribute header** that precedes all efivar data:
- Typically `\x07\x00\x00\x00` (EFI_VARIABLE_NON_VOLATILE | EFI_VARIABLE_BOOTSERVICE_ACCESS | EFI_VARIABLE_RUNTIME_ACCESS)
- Any replacement you write must include this header or the kernel rejects it

**HPMS variable** (5 bytes total: 4-byte attrs header + 1 data byte) — the
single data byte is a password-present flag. Zeroing just this byte is the
**narrowest nuke attempt:** only 1 byte changes, no risk of corrupting BIOS
settings. The data is non-zero when a password is set; write 0x00 to clear.

```bash
# Build replacement: 4-byte header + 0x00 data byte
printf '\\x07\\x00\\x00\\x00\\x00' | sudo tee /sys/firmware/efi/efivars/HPMS-30fef3a5-ba29-4767-9f11-7c7fd606ffa6
```

If this alone doesn't work, escalate to nuking the Setup variable's password
bytes (requires finding the correct offset).

**Alternative approach for when exact offsets are unknown** — nuke the entire Setup variable by replacing it with a known-clean copy from the same BIOS version. This requires finding another machine with the same BIOS but no password, or extracting a clean NVRAM segment from the vendor BIOS image.

**If efivar write fails** (`write error: Device or resource busy`, `Operation not permitted`):
- Check `chattr -i` actually took effect with `lsattr`
- Some kernels have `efivarfs` mounted `noexec` — verify with `mount | grep efivarfs`
- Try `sudo mount -o remount,rw /sys/firmware/efi/efivars/`
- Check Secure Boot state — on some firmware, SB locks efivar modifications

#### Method H: SPI Flash Programmer (hardware — universal)

When all software methods fail, the SPI flash chip can be read/written
externally. This works on every laptop regardless of brand, BIOS vendor,
or password complexity.

**Required hardware:**
- CH341A USB SPI programmer ($5-15)
- SOIC-8 test clip (Pomona 5250 or generic, also ~$5)
- 1.8V adapter (critical — modern laptops run SPI at 1.8V, CH341A defaults to 3.3V)

**The clip:**
A spring-loaded 8-prong clamp that grabs the BIOS EEPROM pins without
desoldering. The clip's ribbon cable connects to the CH341A's ICSP header.
Red wire = pin 1 on both clip and chip.

**Procedure:**
```bash
# Install flashrom
sudo apt install flashrom -y

# Identify the chip — look on the motherboard for an 8-pin SOIC near the
# edge, often under shielding. Common markings:
#   Winbond 25Q64FVSQ (64Mbit/8MB)
#   Winbond 25Q128FVSQ (128Mbit/16MB)
#   MXIC or Macronix 25-series

# Dump the full BIOS
sudo flashrom -p ch341a_spi -r backup.bin
# Verify the dump
sudo flashrom -p ch341a_spi -v backup.bin

# Extract the NVRAM/GUID region, find the password bytes, zero them
# OR: download a clean copy of the same BIOS version from vendor support
# and reflash the whole chip
sudo flashrom -p ch341a_spi -w clean_bios.bin
```

**Caveats:**
- 1.8V vs 3.3V mismatch WILL produce garbage reads or damage the chip
- The clip must align with pin 1 (dot/notch on chip, red wire on clip)
- Laptop must be completely unpowered (battery out, AC unplugged)
- If BIOS has flash descriptor locking, writing may require unlocking the
  flash descriptor region first

## HP-Specific Deep Dive

HP consumer laptops (Pavilion, Envy, Stream) and business (ProBook, EliteBook)
use Insyde H2O UEFI BIOS. The admin password is stored in NVRAM, not CMOS.

### Key discovery path:

1. **Check if hp-bioscfg kernel module loads**
   - `modprobe hp-bioscfg` — if it loads, check `/sys/devices/platform/hp-bioscfg/admin_password/`
   - If `set_password` attribute exists, write empty/nil to clear

2. **WMI interface check**
   - GUID: `05901221-D566-11D1-B2F0-00A0C9062910`
   - Check `ls /sys/bus/wmi/devices/`
   - Dump ACPI tables with `acpidbg` or `cat /sys/firmware/acpi/tables/DSDT`

3. **Setup variable table in NVRAM**
   - The admin password byte is at a model-specific offset in the Setup variable
   - Pattern: look for non-zero bytes in the settings portion of the NVRAM dump
   - Once identified, writing 0x00 clears the password flag

4. **If all else fails**: BIOS recovery (Win+B) with latest vendor BIOS reflash
   will overwrite NVRAM and clear the password — but will also reset all settings.

## Pitfalls

- **CMOS clear does NOT work on UEFI NVRAM passwords** (post-2015 laptops). The
  password is stored in SPI flash with the firmware, not in CMOS SRAM. Removing
  the battery only resets clock/date.
- **hp-bioscfg may not be available** on your kernel version. Ubuntu 24.04's
  kernel (6.8+) includes it; older kernels need it built manually.
- **setup_var offset is model-specific** — an offset that works on one BIOS
  version will be wrong on another. Don't assume.
- **Writing the wrong NVRAM byte** can brick the ability to enter BIOS or boot.
  Always verify the offset from a known source or a dump of the same model.
- **Secure Boot blocks unsigned kernel modules** — if SB is on, you can't
  modprobe hp-bioscfg unless it was built as built-in or signed.
- **Some HP models have dual-password** (admin + user/HDD). Clearing only the
  user password isn't enough — you need the admin password gone.
- **BIOS recovery reflash (Win+B) also clears bitlocker TPM binding** — if the
  drive is encrypted with BitLocker, recovery key will be needed.
- **SPI flash programmer** (external hardware like CH341A) is the nuclear option
  that works on any model if you can access the BIOS chip, but requires
  the SOIC-8 clip and a separate machine.
- **dd and cp fail on efivars** — these sysfs-pseudo files don't support lseek.
  Always use `cat source > dest` for backup.
- **efivar immutable flag** — efivars are marked `chattr +i` by default. Remove
  with `sudo chattr -i /sys/firmware/efi/efivars/Setup-{GUID}` before writing.
- **EFI variable attribute header** — every efivar write must include the 4-byte
  UEFI attributes header (usually `\x07\x00\x00\x00`). Writing raw data without
  this header produces a kernel EINVAL.
- **SPI flash voltage mismatch** — modern laptops (2018+) typically use 1.8V
  SPI. The CH341A defaults to 3.3V. Using 3.3V on a 1.8V chip reads garbage
  and can damage the chip. Always verify voltage requirements from the chip
  datasheet (e.g. Winbond 25Q64FVSIG = 2.7-3.6V, 25Q64FVSIQ = 2.3-3.6V —
  but some are 1.8V-only).

## Reference Files

- `references/hp-pavilion-15-cs0xxx-bios-password.md` — Session-specific detail:
  HP Pavilion 15-cs0xxx (Insyde H2O F.32): exact efivar GUIDs, immutable flags,
  backup method (cat vs dd/cp caveats), SPI flash chip location estimate.
