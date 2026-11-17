# HP Pavilion 15-cs0xxx BIOS Admin Password Recovery

Session reference: 2026-07-15 on lin.

## Hardware

- **Model:** HP Pavilion Laptop 15-cs0xxx
- **CPU:** Intel i7-8550U (Kaby Lake R)
- **BIOS:** Insyde H2O UEFI F.32
- **Serial:** 5CD8373516
- **OS:** Kubuntu 25.04 (kernel 6.17)
- **Tailscale:** 100.91.55.113
- **RTC:** Supercap (no CR2032 coin cell). No CMOS clear jumper visible.
- **No on-screen code after 3 failed BIOS password attempts** — bios-pw.org via serial (5CD8373516) generated `qetufxfq3g` which did NOT work, and no code is displayed on screen for this model.

## Discovered EFI Variables

Ran `ls /sys/firmware/efi/efivars/ | grep -iE '(Setup|HPMS)'`:

| Variable | Size | Immutable? |
|----------|------|------------|
| `Setup-a04a27f4-df00-4d42-b552-39511302113d` | 1804 bytes (1.8K) | Yes (`chattr +i`) |
| `HPMS-30fef3a5-ba29-4767-9f11-7c7fd606ffa6` | 5 bytes | Yes (`chattr +i`) |
| `H19SetupVariable-30fef3a5-ba29-4767-9f11-7c7fd606ffa6` | 21 bytes | No |

All other `*Setup*` vars (CpuSetup, MeSetup, PchSetup, SaSetup, SgxSetupVariable) are also immutable — the kernel locks all setup-related efivars.

The **fixed GUID** across all HP systems for HPMS & H19SetupVariable is `30fef3a5-ba29-4767-9f11-7c7fd606ffa6`. The Setup variable GUID `a04a27f4-df00-4d42-b552-39511302113d` is Insyde H2O GUID-common, but may differ by model.

## Backup Method and Results

`dd` and `cp` FAIL on efivars (they both use lseek which returns ESPIPE on these sysfs-pseudo files). Use `cat`:

```bash
cat /sys/firmware/efi/efivars/Setup-a04a27f4-df00-4d42-b552-39511302113d > ~/bios_backup/Setup.bin
cat /sys/firmware/efi/efivars/HPMS-30fef3a5-ba29-4767-9f11-7c7fd606ffa6 > ~/bios_backup/HPMS.bin
```

Backups saved to `~/bios_backup/`:
- `Setup.bin` — 1804 bytes (4-byte UEFI attrs header `\x07\x00\x00\x00` + 1800 bytes of Setup config data)
- `HPMS.bin` — 5 bytes (4-byte attrs header `\x07\x00\x00\x00` + 1 byte password-present flag)

The HPMS variable is compact enough for the narrowest nuke: write back the 4-byte header + a single `\x00` data byte. No offset hunting required.

## Next Steps (not yet executed)

1. **HPMS narrow nuke** — remove immutable flag on HPMS, write `printf '\x07\x00\x00\x00\x00' | sudo tee ...`, reboot
2. **efivar Setup nuke** — remove immutable flag on Setup, zero password bytes at correct offset, reboot
3. **BIOS recovery flash** — Win+B at power-on with latest F.32 BIOS image on FAT32 USB
4. **SPI flash** — CH341A + SOIC-8 clip on the BIOS EEPROM (Winbond 25Q series)

## Estimated SPI Flash Chip Location

Pavilion 15-cs0xxx uses a Winbond 25Qxx chip (likely 25Q64FVSQ or 25Q128FVSQ), SOIC-8 package, typically near the right edge of the motherboard close to the RAM slots, often under a mylar EMI shielding sticker. May be on underside depending on revision.

## Voltage Note

Intel Kaby Lake-R platforms use 1.8V SPI. A CH341A programmer needs a 1.8V adapter or voltage-level converter chip-side. Verify the actual chip marking before applying voltage.
