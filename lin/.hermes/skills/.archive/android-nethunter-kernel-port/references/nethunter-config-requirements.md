# NetHunter config symbol catalogue

Grouped requirements for a NetHunter kernel, with what each one buys. Verify existence with a tree-wide Kconfig search before trusting the name — symbol names drift between kernel versions and vendor forks:

```bash
grep -rlE "^\s*(config|menuconfig) SYMBOL\b" --include=Kconfig* .
```

## USB gadget — HID / BadUSB / DriveDroid

| symbol | buys |
|---|---|
| `USB_CONFIGFS_F_HID` | BadUSB / HID keystroke injection (the headline Full feature) |
| `USB_CONFIGFS_MASS_STORAGE` | DriveDroid — phone as bootable USB |
| `USB_CONFIGFS_ECM` / `USB_CONFIGFS_ECM_SUBSET` / `USB_CONFIGFS_NCM` | BadUSB network MITM |
| `HIDRAW` | raw HID access for gadget tooling |

Kernel support alone is not sufficient for HID: the ramdisk must expose `/dev/hidg0` and `/dev/hidg1` with the right nodes and permissions. Expect to also need an `init`/`ueventd` rc fragment and `mknod` for the gadget nodes — a kernel with `F_HID=y` and no gadget nodes is a common half-done state.

## External USB WiFi adapters (the injection path)

| symbol | adapter class |
|---|---|
| `ATH9K_HTC` | Atheros AR9271 (2.4 GHz, reliable injection) |
| `RTL8XXXU` + `RTL8XXXU_UNTESTED` | Realtek RTL8188/8192/8723 family |
| `RT2800USB` (+ the `RT2800USB_RT33XX/RT35XX/RT3573/RT53XX/RT55XX/UNKNOWN` sub-options) | Ralink RT3070 / RT5370 |
| `MT7601U` | MediaTek MT7601U |
| `R8188EU` | staging RTL8188EU |

The RTL8812AU-class (5 GHz, the strongest option) is usually an **out-of-tree** driver shipped as a module (`88XXAU`), not an in-tree symbol — check the tree before listing it as available.

Caveat on external-adapter support: it only helps if the ROM's own stack still loads. Anything that changes cfg80211/mac80211 struct layout breaks that, which is why the three forbidden options are forbidden.

## Bluetooth Arsenal

`BT_RFCOMM`, `BT_RFCOMM_TTY` (RFCOMM/HCI raw sockets), `BT_HCIUART` + `_H4` / `_BCM` / `_RTL` (external serial adapters), `BT_HCIBTUSB` (USB dongles).

## SDR

`MEDIA_SDR_SUPPORT` plus the bridge and tuner drivers (`DVB_USB_V2`, `DVB_USB_RTL28XXU`). Many `MEDIA_*` options are pulled in by `MEDIA_SUBDRV_AUTOSELECT`, so enabling the top-level and the USB bridge is often enough.

## CAN / CARsenal

`CAN`, `CAN_RAW`, `CAN_BCM` (core), `CAN_VCAN` + `CAN_SLCAN` (virtual + serial-line CAN). The virtual/serial pair is what makes CAN tooling usable without a hardware adapter.

## Userspace/runtime requirements

| symbol | why |
|---|---|
| `SYSVIPC` | Metasploit + PostgreSQL shared memory |
| `MODULE_FORCE_UNLOAD` | unload modules during driver swapping |
| `NETLINK_DIAG` | socket introspection tools |
| `VSOCKETS` | some container/VM tooling |

## USB-serial bridges

`USB_SERIAL_CH341`, `USB_SERIAL_CP210X` — cheap USB-TTL adapters used for UART consoles and GPS pucks.

## Forbidden — verify absent

```
CONFIG_CFG80211_WEXT
CONFIG_MAC80211_MESH
CONFIG_WIRELESS_WDS
```

All three alter cfg80211/mac80211 structure layout → exported-symbol CRCs change → prebuilt modules refuse to load. They are not worth the feature they nominally enable.
