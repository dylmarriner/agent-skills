# Octoplus Crypto Architecture

Extracted from Octoplus Samsung v5.1.2.2 and FRP v3.0.5.0 during static RE.

## License Validation Protocol

### Server Endpoints
- Primary: `node.octoplusbox.cloud:8443` / `node.octoplusbox.club:8443`
- Fallback: `mussaurus.octoplusbox.club/269C639C2D421A99163EA24710F4ED5D.json`
- Web: `https://octoplusbox.com/en/buynow/`
- APK resources: `https://apk.octoplusbox.cloud/`

### License Flow
1. Smart-card (WinSCard) ← bypassed by stub
2. USB dongle (libusb) ← bypassed by stub
3. HWID-based server validation via HTTPS + JSON
4. AES-GCM tag verification (`check_aes_gcm`)
5. X509 certificate validation (`check_issued`, `check_revocation`, `check_crl`)

### HWID Generation
- Algorithm: PBKDF2-HMAC-SHA512, 5000/9000 iterations
- Source: `SELECT Manufacturer,SerialNumber FROM Win32_PhysicalMemory`
- Class: `TOCTHWID` (Delphi), `bt_PBKDF2_HWID`, `GetHWID`
- Key (81 bytes): base64-encoded blob ending in `_hwid_typen`

### Encryption
- AES-128-GCM for license envelope (`TAESKey` = 16 bytes)
- AES-128-CBC for .oct file decryption (v1.0 format)
- AES-128-CFB for .orf file decryption (v2.0 format, via MetaCore.dll Crypto++)
- INIT_KEY_1: 52 bytes at code offset
- INIT_KEY_2: 84 bytes at code offset
- RSA public key embedded for signature verification (`PubKey=40000000B7...`)

### Embedded Certificate
- PEM header found in OctoplusSamsungNew.exe at 0x1c388a0
- Hex-encoded: `2D2D2D2D2D424547494E2043455254494649434154452D2D2D2D2D...`
- Private key reference at 0x1cab0d5: `-----BEGIN PRIVATE KEY-----`

## Encrypted File Formats (.oct / .orf)

### .oct (v1.0) — Samsung Tool
```
Offset 0: "OCTOPUS_v.1.0\0\0\0" (16 bytes magic)
Offset 16: encrypted payload (AES-CBC)
```

### .orf (v2.0) — FRP Tool  
```
Offset 0: "OCTOPUS_v.2.0\0\0\0" (16 bytes magic)
Offset 16: IV (16 bytes)
Offset 32: encrypted payload (AES-CFB via Crypto++)
```

### Known IV Groups
| Group | IV (hex) | Used by |
|-------|----------|---------|
| Main | `f647c0f93b71a0c4915c406aa035a05c` | MTKLoaders, QComLoaders, HWDrv, SPDLoaders, AMobile |
| Unisoc | `69003595fef6c855ccb26638541012c6` | All Tiger/SC-series Unisoc loaders |

### Key Location
AES keys are in MetaCore.dll (14MB of statically linked Crypto++). The key is either:
1. Hardcoded as a 16-byte constant in MetaCore.dll
2. Derived at runtime from a server-provided value
Without the physical Octoplus Box to trigger runtime decryption, static extraction is time-consuming (the key is one byte pattern among 14MB of Crypto++ code).

## Chipset Protocols

### MediaTek (MetaCore.dll / OctoplusFRP)
- Preloader mode: BROM/DA protocol via libusb on VID 0E8D
- Boot modes: META, ADVMETA, ATEFactory, Fastboot
- GFH file format: GFH_FILE_INFO, GFH_BL_INFO, GFH_BL_SEC_KEY, GFH_ANTI_CLONE
- USB download commands: USBDL setup, secure authentication, image info check

### Qualcomm (OctoplusSamsung)
- Sahara/Firehose/EDL/9008 protocols
- DIAG serial commands (AT protocol over serial)
- Fastboot boot mode
- CTS decryption mode

### Exynos (OctoplusSamsung)
- Repurposed NVIDIA Tegra flash stack: RCM + 3P + WinUSB
- DWC3 USB 3.0 controller buffer overflow exploits
- CPDN (Compelson) protocol
- Shannon HWID, IMEI certificate repair

### NVIDIA Tegra (OctoplusSamsung)
- Full nvflash DLL stack: libnv3p, libnvaes_ref, libnvapputil, libnvboothost, libnvflash, libnvos, libnvusbhost
- APX recovery mode

## rd.exe — Standalone Tool

- Ext4 Worker v1.0.1 by Octoplus (C++ console app, Boost + lwext4)
- Mounts ext4 images, patches IMEI at `md/NVRAM/NVD_IMEI/LD0B_001`
- Works under Wine without dongle or license

## SAM_ALL.db — Model Database
SQLite with 2136 Samsung model strings. Tables: `models(name text)`

## Hydra Tool V7.0

Also Smart Install Maker v5.04, 2.7GB overlay. Password unknown (not 1234). Needs real Windows VM for extraction.

## QEMU Windows VM Setup

For tools requiring real Windows:
```
qemu-system-x86_64 -machine type=pc,accel=tcg -cpu max -smp cores=2 -m 3072 \\
  -drive file=disk.qcow2,format=qcow2,if=virtio \\
  -cdrom Win11.iso \\
  -drive file=virtio-win.iso,format=raw,if=virtio,media=cdrom \\
  -nic user,model=virtio-net-pci \\
  -vga virtio -display none -vnc :1
```
Port 5901 for VNC. Win11 25H2 ISO: 8.1GB. Virtio drivers: 692MB.
