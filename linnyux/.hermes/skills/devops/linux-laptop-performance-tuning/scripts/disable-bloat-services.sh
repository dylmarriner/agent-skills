#!/bin/bash
# disable-bloat-services.sh
#
# Disables non-essential services on Ubuntu 24.04 desktop to reduce
# boot time and background CPU/memory overhead.
#
# Usage:
#   sudo bash disable-bloat-services.sh [--dry-run]
#
# Each service includes an inline justification so you can decide
# whether to skip it. Services are safe to disable on a dev laptop.

set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "=== DRY RUN - no changes will be made ==="
fi

services=(
  "plocate-updatedb.timer:File indexing database - saves ~30s boot time, run updatedb manually when needed"
  "plocate-updatedb.service:Same as above, also disable the service unit"
  "unattended-upgrades.service:Automatic apt upgrades - causes random apt lock contention during work"
  "rsyslog.service:System logging - redundant with systemd-journald"
  "kerneloops.service:Kernel crash submission - diagnostic only, not needed for daily use"
  "teamviewerd.service:Remote desktop daemon - disable if you don't use TeamViewer"
  "smartmontools.service:SMART disk monitoring - not useful for NVMe daily use"
  "apt-daily-upgrade.timer:Daily apt upgrade check - causes CPU spikes"
  "apt-daily.timer:Daily apt update check - causes CPU spikes"
)

for entry in "${services[@]}"; do
  name="${entry%%:*}"
  reason="${entry#*:}"
  echo ""
  echo "=== $name ==="
  echo "  Reason: $reason"

  if systemctl is-enabled --quiet "$name" 2>/dev/null; then
    if [[ "$DRY_RUN" == "true" ]]; then
      echo "  WOULD DISABLE"
    else
      sudo systemctl disable --now "$name" 2>&1 && echo "  DISABLED" || echo "  ALREADY DISABLED"
    fi
  else
    echo "  Not currently enabled (already disabled or doesn't exist)"
  fi
done

echo ""
echo "=== Done ==="
echo "Remaining running services (non-kernel):"
systemctl list-units --type=service --state=running --no-pager --plain | grep -v "@" | head -20
echo ""
echo "=== Verify boot impact ==="
systemd-analyze blame 2>/dev/null | head -10
