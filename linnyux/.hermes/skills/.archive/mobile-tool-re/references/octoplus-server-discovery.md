# Octoplus Server & Infrastructure Discovery

Discovered during reverse engineering of Octoplus Samsung v5.1.2.2 and Octoplus FRP v3.0.5.0.

## License Servers

```
node.octoplusbox.cloud
node.octoplusbox.club
```

Both endpoints resolve. The "node." prefix suggests a distributed node network for license validation, not a single centralized server. The `.club` TLD is unusual and may be a backup/failover domain.

## HWID System

The HWID is computed using PBKDF2, as evidenced by these identifiers in OctoplusSamsung.exe:

```
bt_PBKDF2_HWID
FHWIDHash1
GetHWID
```

A base64-encoded key blob was found in the binary at offset 0x1051e8:

```
7QxDHBCSemNzO0epsBDqw2tZ3Ig_V4kkTxsU0w9zvSvNOm5hd5+4zUg_4ydUdHa1UY2c6VoF6FKZ1SXX8TA_KhG0KJR94V7uH+RBiEjIvwRDC6E_hwid_typen
```

This appears to be a HWID derivation key or challenge seed (base64, ~140 chars). The `_hwid_typen` suffix suggests it's a typed HWID with multiple variants.

## Auth & Validation Components

Extracted from strings in OctoplusSamsung.exe:

```
AAuthentication
AddAuthentication
algorithm_auth
AM_LOGIN
TIdX509Fingerprints
check_aes_gcm
check_crl
check_hashes
check_issued
check_odex
check_revocation
check_gaf_checksum
```

- X509 certificate fingerprint verification (`TIdX509Fingerprints` — Indy library component)
- AES-GCM encryption for secure channels
- CRL (Certificate Revocation List) checking
- GAF checksum (proprietary algorithm)

## Error Codes

| String | Meaning |
|--------|---------|
| `NG NEEDAKAUTH` | Authentication token required |
| `NG NEEDMSLAUTH` | Microsoft License auth required? |
| `29 User authentication failed` | Generic auth failure |
| `30 Activation rejected by GGSN` | GGSN (Gateway GPRS Support Node) activation rejected |
| `31 Activation rejected, unspecified` | Generic activation failure |
| `57 Bearer capability not authorized` | Bearer/service not on plan |

## UI Elements

```
Activation Info
ActivationinfoButton
activationStrEdit
Don't show credits and latest news at Software start
A new version of Octoplus Box Samsung Software is available!
```

## Sprint Unlock (US Carrier)

```
assets/OctoPlusSprint
assets/OctoPlusSprintPK
GetSprintSNOnce
getSprintLockState
GetSprintMSLCertStatusk
GSprintEraseAllEfsS10Unit
SprintUnlockHongNote10RestoreEFSUnit
```

Sprint-specific unlock functions, including MSL certificate handling and EFS restore.

## Supported Models

SQLite database `SAM_ALL.db` contains 2,136 Samsung models.

Encrypted model list `SamsungModels.oct` has the OCTOPUS_v.1.0 header and encrypted binary payload — likely the same model list but with additional parameters (chipset type, protocol variant, unlock capabilities).

## Console Worker (rd.exe)

`rd.exe` is a C++ console application (298KB) that handles actual device communication:
- Uses Boost C++ libraries
- `lwext4` library for ext4 filesystem operations
- `DeviceIoControl` for Windows USB device access
- IMEI read/write operations
- Ext4 partition mounting
- Keystore access
