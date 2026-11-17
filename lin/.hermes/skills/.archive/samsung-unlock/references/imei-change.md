# Samsung IMEI Change Methods

Class: Modem/NVRAM modification for Samsung Exynos devices.

Target: Galaxy A54 (SM-A546E, Exynos 1380)

## Method 1: Commercial Tools (Windows)

- **Octoplus Samsung** v5.1.2.2 — dongle required
- **Z3X Samsung Tool Pro** — box/dongle or server credits
- **Chimera Tool** — server credits (no dongle)

All extracted at /home/kubuntux/Downloads/RE/

## Method 2: Root + EFS Direct

Exynos 1380 stores IMEI on /dev/block/m9kefs1 and m9kefs2:
```
adb shell su -c "dd if=/dev/block/m9kefs1 of=/data/local/tmp/m9kefs1.img"
adb pull /data/local/tmp/m9kefs1.img
# hex-edit IMEI (15 ASCII digits, may appear multiple times)
adb push new.img /data/local/tmp/
adb shell su -c "dd if=/data/local/tmp/new.img of=/dev/block/m9kefs1; sync"
adb reboot
```
Verify: `adb shell "echo 'AT+CGSN' > /dev/smd0 && cat /dev/smd0"`

## Method 3: Eng Bootloader + AT

`AT+EGMR=1,7,"IMEI"` — Knox 3.0+ blocks this on recent firmware.

## Method 4: Protocol Capture (RE in progress)

DLL interposer on libusb-1.0.dll + usbmon on host.
