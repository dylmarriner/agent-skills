#!/usr/bin/env bash
# Read-only device presence ladder for Linux. Performs NO writes.
# Usage: device-presence-probe.sh [grep-keyword]
#   default keyword: 'network|wireless|audio|bluetooth'
set -uo pipefail

KW="${1:-network|wireless|audio|bluetooth}"

section() { printf '\n== %s ==\n' "$1"; }

section "identity (firmware = authoritative; hostname is only a label)"
for f in sys_vendor product_name product_version board_name bios_version bios_date; do
  printf '  %-14s %s\n' "$f" "$(cat "/sys/class/dmi/id/$f" 2>/dev/null || echo '?')"
done
printf '  %-14s %s\n' "hostname" "$(hostnamectl --static 2>/dev/null || hostname)"
sudo -n true 2>/dev/null && echo '  sudo: passwordless' || echo '  sudo: needs password'

section "PCI devices matching /$KW/ (with bound driver)"
lspci -nnk 2>/dev/null | grep -iE -A2 "$KW" || echo '  (no match)'

section "every PCI function: class, address, bound driver"
for d in /sys/bus/pci/devices/*; do
  c=$(cat "$d/class" 2>/dev/null) || continue
  drv=$(basename "$(readlink -f "$d/driver" 2>/dev/null)" 2>/dev/null)
  printf '  %s %s %s\n' "$c" "$(basename "$d")" "${drv:--}"
done | sort

section "USB devices"
lsusb 2>/dev/null || echo '  (lsusb unavailable)'

section "kernel class subsystems"
for s in ieee80211 sound drm bluetooth; do
  printf '  /sys/class/%-12s %s\n' "$s" "$(ls "/sys/class/$s" 2>/dev/null | tr '\n' ' ')"
done
printf '  /dev/video*          %s\n' "$(ls /dev/video* 2>/dev/null | tr '\n' ' ')"
printf '  /dev/snd             %s\n' "$(ls /dev/snd 2>/dev/null | tr '\n' ' ')"

section "wireless/bluetooth firmware on disk (distro ships *.zst — match the prefix)"
ls /lib/firmware 2>/dev/null | grep -iE 'iwlwifi|rtw|rtl8|mt7|ath9k|btintel|ibt' | head -25

section "kernel log (EMPTY = driver never saw a device; firmware errors say so loudly)"
dmesg 2>/dev/null | grep -iE 'iwlwifi|iwlmvm|rtw|rtl8|mt7|ath9k|bluetooth|firmware' | tail -20

printf '\nNo writes performed. To force a re-probe:\n'
printf "  sudo -n sh -c 'echo 1 > /sys/bus/pci/rescan' && sudo modprobe -r <module> && sudo modprobe <module>\n"
