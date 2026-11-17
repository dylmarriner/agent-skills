# iPad Model → Chip → checkm8 Exploit Compatibility

Compiled July 2026. All iPad models and their checkm8 (bootrom exploit) vulnerability status.

## Legend

- **checkm8 ✓** = A5–A11 chip, vulnerable to bootrom exploit. Permanent, unpatchable iCloud bypass possible via checkra1n/palera1n.
- **checkm8 ✗** = A12+ or Apple Silicon. No public bootrom exploit. Tethered signal bypass only (paid services, comes back after restore).

## iPad (Standard)

| Generation | Release | Chip | checkm8 |
|---|---|---|---|
| iPad (1st) | Apr 2010 | A4 | ✓ |
| iPad 2 | Mar 2011 | A5 | ✓ |
| iPad (3rd) | Mar 2012 | A5X | ✓ |
| iPad (4th) | Nov 2012 | A6X | ✓ |
| iPad (5th) | Mar 2017 | A9 | ✓ |
| iPad (6th) | Mar 2018 | A10 Fusion | ✓ |
| **iPad (7th)** | **Sep 2019** | **A10 Fusion** | **✓ ← latest checkm8** |
| iPad (8th) | Sep 2020 | A12 Bionic | ✗ |
| iPad (9th) | Sep 2021 | A13 Bionic | ✗ |
| iPad (10th) | Oct 2022 | A14 Bionic | ✗ |
| iPad (11th) | Mar 2025 | A16 | ✗ |

## iPad Pro

| Generation | Release | Chip | checkm8 |
|---|---|---|---|
| 12.9" (1st) | Nov 2015 | A9X | ✓ |
| 9.7" | Mar 2016 | A9X | ✓ |
| 12.9" (2nd) / 10.5" | Jun 2017 | A10X Fusion | ✓ |
| 11" (1st) / 12.9" (3rd) | Nov 2018 | A12X Bionic | ✗ |
| 11" (2nd) / 12.9" (4th) | Mar 2020 | A12Z Bionic | ✗ |
| 11" (3rd) / 12.9" (5th) | May 2021 | M1 | ✗ |
| 11" (4th) / 12.9" (6th) | Oct 2022 | M2 | ✗ |
| 11" / 13" (7th) | May 2024 | M4 | ✗ |
| 11" / 13" (8th) | Oct 2025 | M5 | ✗ |

## iPad Air

| Generation | Release | Chip | checkm8 |
|---|---|---|---|
| Air (1st) | Nov 2013 | A7 | ✓ |
| Air 2 | Oct 2014 | A8X | ✓ |
| Air (3rd) | Mar 2019 | A12 | ✗ |
| Air (4th) | Oct 2020 | A14 | ✗ |
| Air (5th) | Mar 2022 | M1 | ✗ |
| Air 11"/13" (6th) | May 2024 | M2 | ✗ |
| Air 11"/13" (M3) | Mar 2025 | M3 | ✗ |
| Air 11"/13" (M4) | Mar 2026 | M4 | ✗ |

## iPad mini

| Generation | Release | Chip | checkm8 |
|---|---|---|---|
| mini (1st) | Nov 2012 | A5 | ✓ |
| mini 2 | Nov 2013 | A7 | ✓ |
| mini 3 | Oct 2014 | A7 | ✓ |
| mini 4 | Sep 2015 | A8 | ✓ |
| mini (5th) | Mar 2019 | A12 | ✗ |
| mini (6th) | Sep 2021 | A15 | ✗ |
| mini (7th, A17 Pro) | Oct 2024 | A17 Pro | ✗ |

## Quick Reference

**All checkm8-vulnerable iPads:**
- iPad (7th gen) and earlier — A10 or older
- iPad Pro 12.9" (2nd gen) / 10.5" — A10X
- iPad Pro 12.9" (1st gen) / 9.7" — A9X
- iPad Air 2 — A8X
- iPad Air (1st) — A7
- iPad mini 4 — A8
- iPad mini 3/2 — A7
- iPad mini (1st) — A5

**Latest checkm8-vulnerable iPad by line:**
- Standard: **iPad (7th gen)** — A10 Fusion — Sep 2019
- Pro: **12.9" (2nd) / 10.5"** — A10X — Jun 2017
- Air: **Air 2** — A8X — Oct 2014
- mini: **mini 4** — A8 — Sep 2015

## Practical Notes

- checkm8-based bypass (checkra1n/palera1n) gives a **tethered iCloud bypass**. True iCloud removal requires server-side FMI OFF via IMEI (rare, expensive).
- A12+ iPads can only use: paid signal-based bypass (tethered, Mac-only for recent models), DNS bypass (crippled, no iMessage/Facetime), or server-side FMI OFF.
- iPad (7th gen) runs iPadOS up to 18.x — checkra1n/palera1n compatibility should be verified per release.
