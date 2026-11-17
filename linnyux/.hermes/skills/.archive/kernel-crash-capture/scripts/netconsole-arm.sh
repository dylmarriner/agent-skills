#!/usr/bin/env bash
# Arm dynamic (configfs) netconsole so kernel messages leave the box over UDP and
# survive a hard freeze / power event on a collector machine.
#
# Usage:   sudo REMOTE_IP=192.168.1.225 ./netconsole-arm.sh
# Env:     REMOTE_IP   (required) collector address
#          REMOTE_PORT (default 6666)
#          LOCAL_IP    (default: primary IPv4 of the default-route interface)
#          LOCAL_IF    (default: interface of the default route)
#          LOCAL_PORT  (default 6666)
set -u

REMOTE_IP="${REMOTE_IP:?set REMOTE_IP to the collector address}"
REMOTE_PORT="${REMOTE_PORT:-6666}"
LOCAL_PORT="${LOCAL_PORT:-6666}"

LOCAL_IF="${LOCAL_IF:-$(ip route show default | awk '{print $5; exit}')}"
LOCAL_IP="${LOCAL_IP:-$(ip -4 -o addr show dev "$LOCAL_IF" | awk '{print $4}' | cut -d/ -f1 | head -1)}"

TARGET_DIR=/sys/kernel/config/netconsole/target1
MAC_RE='([0-9a-f]{2}:){5}[0-9a-f]{2}'

modprobe netconsole 2>/dev/null || true
mountpoint -q /sys/kernel/config || mount -t configfs none /sys/kernel/config 2>/dev/null || true
[ -d /sys/kernel/config/netconsole ] || { echo "netconsole configfs unavailable" >&2; exit 1; }

# MAC must come from a pattern match: `ip neigh` shifts field positions when `dev` is given.
REMOTE_MAC=$(ip neigh show "$REMOTE_IP" 2>/dev/null | grep -oE "$MAC_RE" | head -1)
for _ in 1 2 3; do
    [ -n "$REMOTE_MAC" ] && break
    ping -c1 -W2 "$REMOTE_IP" >/dev/null 2>&1 || true
    sleep 1
    REMOTE_MAC=$(ip neigh show "$REMOTE_IP" 2>/dev/null | grep -oE "$MAC_RE" | head -1)
done
[ -n "$REMOTE_MAC" ] || { echo "cannot resolve $REMOTE_IP MAC (is the collector up and on this L2?)" >&2; exit 1; }

mkdir -p "$TARGET_DIR"
printf '%s\n' "$LOCAL_IP"    > "$TARGET_DIR/local_ip"
printf '%s\n' "$LOCAL_PORT"  > "$TARGET_DIR/local_port"
printf '%s\n' "$LOCAL_IF"    > "$TARGET_DIR/dev_name"
printf '%s\n' "$REMOTE_IP"   > "$TARGET_DIR/remote_ip"
printf '%s\n' "$REMOTE_PORT" > "$TARGET_DIR/remote_port"
printf '%s\n' "$REMOTE_MAC"  > "$TARGET_DIR/remote_mac"
printf '1\n'                 > "$TARGET_DIR/enabled"

echo "netconsole armed: $LOCAL_IP:$LOCAL_PORT ($LOCAL_IF) -> $REMOTE_IP:$REMOTE_PORT ($REMOTE_MAC)"
echo "verify: cat /proc/consoles | grep netcon0"
echo "verify: echo '<0>PROBE' | sudo tee /dev/kmsg   # then check the collector's log"
