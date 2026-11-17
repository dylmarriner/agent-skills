# Wireless Radio Triage (Linux)

The most common version of "install the wifi drivers". Work the general presence
ladder first; this file is the wireless-specific reading of it.

## The tells

| Probe | Result | Means |
|---|---|---|
| `lspci -nn` / class enumeration | no `0x02*` device beyond the ethernet NIC | no WiFi function on the bus |
| `ls /sys/class/ieee80211/` | empty | no phy registered, so no usable radio |
| `iw dev` | empty | nothing for the driver stack to configure |
| `rfkill list all` | only `hci0`, no `phy0` | no wireless phy, and no hard/soft-block to clear |
| `dmesg \| grep -i iwlwifi` (or rtw/ath/mt) | **empty** | driver never got a device to probe — not a firmware problem |
| `lsusb` | an Intel BT function present (e.g. `8087:0a2b`) | the **combo module is physically installed** |
| `lspci -vv` root port | `LnkSta: ... Width x0` | port never trained a link |
| `modinfo <mod> \| grep -c '^alias:'` | hundreds | kernel driver support is complete — do not chase a driver package |
| `ls /lib/firmware/<mod>-*` | `.ucode.zst` files present | firmware already shipped by `linux-firmware` |

BT and WiFi are independent halves of one M.2 module: BT rides USB, WiFi rides
PCIe. **BT enumerating while WiFi does not proves the module is present and its
PCIe function is not enumerating** — that is the case to report, not "no wifi
hardware".

## Order of work

1. Identity (DMI) → tells you which part the machine should have.
2. Class-level PCI enumeration → is there a WiFi function at all.
3. `lsusb` for the BT half → module present or genuinely absent.
4. Driver/firmware inventory (`modinfo`, `/lib/firmware/*`) → is anything
   installable even missing. Usually the answer is no, and saying so early stops
   the whole task from becoming a package hunt.
5. Vendor BIOS attribute → "Wireless Network Device (WLAN)" on HP.
6. Non-destructive re-probe (rescan + module reload).
7. Verdict + physical ladder.

## Physical ladder to hand back

```bash
# 1. power drain: clears a stuck PCIe function. Zero cost, do first.
sudo shutdown -h now     # then unplug AC, hold power 15-20s, boot, re-check: lspci -nn | grep 0280
# 2. BIOS setup (F10 on HP) -> Load Setup Defaults; re-arms whole device policy
# 3. reseat the M.2 key-E card in the WLAN slot (NOT the key-B WWAN slot), boot, re-check
# 4. replace module, or USB dongle (see adapters below)
```

Software cannot distinguish a dead card half, a card in a slot without PCIe to
the WiFi function, a BIOS refusal to enable the function, and a faulty slot. Say
so, and let steps 1-3 separate them.

## HP firmware-attributes names

`/sys/class/firmware-attributes/hp-bioscfg/attributes/` (requires `hp_bioscfg`):

- `Wireless Network Device (WLAN)` — the one that matters; `Enable`/`Disable`
- `Bluetooth`, `Embedded LAN controller`, `Lock Wireless Button`
- `Wake on WLAN`, `LAN ! WLAN Auto Switching`

A device can be absent from the bus while this flag reads `Enable` — that result
rules the flag in, so do not stop at "BIOS says enable" and call the case closed.

## Adapters

In-kernel on a current Ubuntu (monitor mode / injection capable marked ★):
`mt7921u` ★, `rtw88_8822bu`, `rtl8xxxu`, `ath9k_htc` ★. On a machine with these
present, an external adapter needs **no install at all** — plug in and check
`iw dev`.

Out-of-tree (DKMS), only for the Realtek dongles that need it:
`sudo apt install realtek-rtl88xxau-dkms` — requires headers + `dkms` (already
standard), and on Secure Boot also `mokutil --sb-state` / an enrolled MOK.

Aircrack tooling is not installed by default: `sudo apt install aircrack-ng`, then
`sudo airmon-ng start <iface>`.
