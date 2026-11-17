#!/usr/bin/env bash
# Deploy network tuning to the fleet: lin, kubuntux, macuntu, rabuntu
# Run from lin (has SSH access to all)
set -euo pipefail

CONF_CONTENT=$(cat << 'SYSCONF'
# Network performance tuning - Hermes fleet
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 131072 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_slow_start_after_idle = 0
net.core.netdev_max_backlog = 50000
net.core.optmem_max = 65536
net.ipv4.tcp_mtu_probing = 1
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_sack = 1
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_dsack = 1
net.ipv4.tcp_timestamps = 1
SYSCONF
)

SMB_CONF_LINES=$(cat << 'SMBCONF'
# Samba server tuning — add to [global] section of /etc/samba/smb.conf
use sendfile = yes
aio read size = 16384
aio write size = 16384
read raw = yes
write raw = yes
server signing = disabled
strict rename = yes
socket options = TCP_NODELAY IPTOS_LOWDELAY
SMBCONF
)

deploy_sysctl() {
    local host=$1
    echo "→ Deploying sysctl to $host"
    echo "$CONF_CONTENT" | ssh "$host" "sudo tee /etc/sysctl.d/90-network-performance.conf > /dev/null && sudo sysctl -p /etc/sysctl.d/90-network-performance.conf" 2>/dev/null | grep -E '(rmem_max|wmem_max|fastopen|slow_start|mtu_probing|backlog)'
}

deploy_samba() {
    local host=$1
    echo "→ Deploying Samba tuning to $host (server)"
    ssh "$host" "grep -q 'aio read size' /etc/samba/smb.conf 2>/dev/null && echo '  already tuned' || { echo '  add to [global]:'; echo '$SMB_CONF_LINES'; }"
    ssh "$host" "sudo systemctl restart smbd 2>/dev/null && echo '  smbd restarted' || echo '  smbd not found'"
}

echo "=== Network tuning deployment ==="
deploy_sysctl "localhost"
deploy_sysctl "kubuntux"
deploy_sysctl "macuntu"
deploy_sysctl "rabuntu@rabuntu"

echo ""
echo "=== Samba server tuning ==="
deploy_samba "kubuntux"

echo ""
echo "=== Verification ==="
for host in "localhost" "kubuntux" "macuntu" "rabuntu@rabuntu"; do
    echo "--- $host ---"
    ssh "$host" "sysctl net.core.rmem_max net.core.wmem_max net.ipv4.tcp_fastopen net.ipv4.tcp_congestion_control" 2>/dev/null
done
