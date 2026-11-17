#!/bin/bash
# Fleet Status Script — Quick health check for all servers
# Part of server-management skill

echo "=========================================="
echo "  FLEET STATUS — $(date '+%Y-%m-%d %H:%M %Z')"
echo "=========================================="
echo ""

check_server() {
  local name=$1
  local ssh_cmd=$2
  local result
  result=$(timeout 8 $ssh_cmd "echo UP && uptime -p && free -h | grep Mem && df -h / | tail -1" 2>&1)
  local status=$?
  
  if [ $status -eq 0 ] && echo "$result" | grep -q "UP"; then
    echo "  🟢 $name — Online"
    echo "$result" | tail -n +2 | while IFS= read -r line; do
      echo "     $line"
    done
  else
    echo "  🔴 $name — Offline / Unreachable"
    echo "     $(echo "$result" | head -1)"
  fi
  echo ""
}

# Local Pi
echo "--- Local (pi5-deflab) ---"
echo "  🟢 Online"
echo "     Uptime: $(uptime -p)"
echo "     Memory: $(free -h | awk '/Mem/ {print $3 " / " $2}')"
echo "     Disk:   $(df -h / | tail -1 | awk '{print $3 " / " $2}')"
echo "     Docker: $(docker ps -q | wc -l) running"
echo ""

# Remote servers
echo "--- Remote Servers ---"
check_server "Kubuntux (15GB/8c)" "ssh -o ConnectTimeout=5 root@kubuntux-to-be-filled-by-o-e-m.tail2c15c8.ts.net"
check_server "Macuntu (7.7GB/4c)" "ssh -o ConnectTimeout=5 -i ~/.ssh/id_ed25519 macuntu@100.75.23.127"
check_server "Cloud (30GB/16c)"  "ssh -o ConnectTimeout=5 -i ~/.ssh/id_ed25519 root@100.102.4.39"

echo "=========================================="
echo "  Docker Stack (This Pi)"
echo "=========================================="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null
echo ""

echo "=========================================="
echo "  Tailscale Peers (Online)"
echo "=========================================="
tailscale status 2>/dev/null | grep "active;" | awk '{print "  🟢 " $2}'
echo ""
echo "Done."
