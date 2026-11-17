# Chimera Tool — Samsung KG Bypass Reference

## Overview
- Website: chimeratool.com
- Platform: **Windows only** (Win 10/11, 32/64-bit)
- Latest version: 47.24.1406 (Jul 2, 2026)
- Installer: 14.46 MB
- Samsung KG Bypass added: March 25, 2026 (v46.53.1220)

## Pricing (Annual)

| License | Price | Credits/yr | Procedure Discount | Phone Connections | Computers |
|---------|-------|------------|-------------------|-------------------|-----------|
| Basic | $99.9 | 999 | 0% | 100 | 8 |
| Professional | $149.9 | 1,499 | 10% | 1,500 | 24 |
| Premium | ~$299 | ~3,000 | 20%+ | Unlimited | Unlimited |

- Each paid procedure costs credits (varies by operation)
- FRP removal typically 10-50 credits
- KG Bypass credit cost not publicly listed (need login)
- Professional/Premium include USB Authenticator (hardware key for portability)
- Premium gets priority customer support
- IMEI blacklist checks: Basic=2/quarter, Professional=6/quarter
- Samsung ML checks included in all tiers

## Supported Samsung Features
- Repair IMEI
- Repair MAC
- Patch Certificate
- Reset FRP Lock / FRP Remove
- Network Factory Reset
- Read Codes Online
- Update Firmware
- Unlock / Relock Bootloader
- CSC Change
- Device Info
- Read/Write Certificate
- Store/Restore Backup
- **Samsung KG Bypass** (added March 2026)

## Supported Chips
Exynos, Qualcomm, Unisoc, Mediatek, Kirin

## Linux Workarounds

### Option 1: Windows VM + USB Passthrough (Recommended)
```bash
# Using Virt-Manager (KVM)
# 1. Create Windows 10/11 VM
# 2. Install Chimera Tool in VM
# 3. Pass through Samsung USB device:
virt-manager → VM Details → Add Hardware → USB Host Device → Samsung
# Or via CLI:
virsh attach-device <vm-name> /path/to samsung-usb.xml

# USB XML for Samsung (edit vendor/product IDs):
# <hostdev mode='subsystem' type='usb'>
#   <source>
#     <vendor id='0x04e8'/>
#     <product id='0x6860'/>
#   </source>
# </hostdev>
```

### Option 2: Wine (Experimental)
- Chimera is .NET-based, may work under Wine with .NET framework
- Not officially supported, may have USB access issues
- Try: `wine ChimeraTool_Installer.exe`

### Option 3: Windows on USB
- If spare machine available, install Windows + Chimera there
- Use Samsung USB on that machine

### Option 4: Dual Boot
- Install Windows alongside Linux on same machine
- Boot into Windows for Chimera operations

## USB Passthrough Notes
- Phone must be in normal boot mode (PID 6860) for KG Bypass
- NOT download mode
- USB passthrough in VM may need libvirt/qemu USB redirect configured
- If USB not detected in VM, try adding USB device filter in virt-manager

## Changelog Highlights
- v46.53.1220 (Mar 25, 2026): Samsung KG Bypass + General Improvements
- v46.70.0703 (May 14, 2026): 168 Models Now Supported by Network Factory Reset
- v47.24.1406 (Jul 2, 2026): Unlock/Relock Bootloader + General Improvements

## Contact
- Telegram: @chimeratoolofficialsupport
- Phone: (+1) 2209002048 (working days 08h-16h GMT)
- Languages: Arabic, Chinese, Spanish, French, Hungarian, English, Italian, Japanese, Portuguese, Russian, Turkish
