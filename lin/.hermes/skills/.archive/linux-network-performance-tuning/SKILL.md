---
name: linux-network-performance-tuning
description: Tune Linux TCP stack, CIFS/Samba mounts, and Tailscale network performance across a fleet of machines. Covers sysctl tuning, Samba server config, CIFS client mount options, and verification.
trigger: When the user says speed up the network, tune TCP, fix slow CIFS, optimize Samba, improve Tailscale throughput, or sysctl network tuning.
---

# Linux Network Performance Tuning

Class of work: optimizing TCP networking, CIFS/Samba file sharing, and Tailscale-aware throughput across a fleet of Linux machines.

## Preliminary Diagnostics

Before tuning, gather baseline data about the network stack:

```bash
# 1. Link speed & duplex — should be 1000/full for gigabit
cat /sys/class/net/eth0/speed /sys/class/net/eth0/duplex
ethtool eth0 2>/dev/null | grep -iE 'speed|duplex|link' | head -5

# 2. Driver & offload status — TSO/GSO/GRO/rx/tx checksum should all be ON
ethtool -i eth0 2>/dev/null
ethtool -k eth0 2>&1 | grep -E 'tcp-segmentation|generic-segmentation|generic-receive|large-receive|rx-checksumming|tx-checksumming|scatter-gather'

# 3. IRQ balance — should be running (1 process)
ps aux | grep -c "[i]rqbalance"

# 4. RPS (Receive Packet Steering) — all rx queues should have non-zero CPU mask
cat /sys/class/net/eth0/queues/rx-*/rps_cpus
# "00" = disabled (all interrupts on CPU 0 only — fix this, see below)

# 5. Current TCP congestion control — should be BBR
sysctl net.ipv4.tcp_congestion_control net.core.default_qdisc

# 6. CPU governor — should be 'performance'
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

# 7. Interrupt distribution — check if interrupts are balanced
cat /proc/interrupts | grep eth0

# 8. Buffer sizes
sysctl net.core.rmem_max net.core.wmem_max net.core.rmem_default net.core.wmem_default
sysctl net.ipv4.tcp_rmem net.ipv4.tcp_wmem

# 9. Initial internet speed test
curl -s -o /dev/null -w "Cloudflare DL: %{speed_download} B/s\n" --max-time 15 'https://speed.cloudflare.com/__down?bytes=25000000'

# 10. Ping to internet
ping -c 5 -W 3 1.1.1.1 | tail -3
```

## TCP Stack Tuning

### The 212KB bottleneck

Default Ubuntu socket buffer max (`rmem_max` / `wmem_max`) is 212KB, which clamps single-connection TCP throughput to ~170Mbps regardless of link speed. This affects SCP, rsync, CIFS, HTTP, Tailscale, and any other single-stream transfer.

### Default buffer sizes matter too

`rmem_default` / `wmem_default` (also 212KB) control the initial socket buffer before auto-tuning kicks in. Raising them to 256KB prevents small-buffer stalls early in the connection lifecycle.

### Consolidated sysctl config

Create `/etc/sysctl.d/99-network-speed.conf` with ALL of the following:

```
# === TCP Stack Speed Tuning ===

# Default socket buffer sizes (prevent early-connection stalls)
net.core.rmem_default = 262144
net.core.wmem_default = 262144

# Max socket buffer sizes (remove the 212KB hard cap)
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216

# TCP auto-tuning buffers: min / default / max (bytes)
net.ipv4.tcp_rmem = 4096 131072 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# TCP fastopen (client+server) — saves one RTT on each new connection
net.ipv4.tcp_fastopen = 3

# BBR congestion control + fq qdisc (best for throughput on lossy/latent links)
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq

# Don't reset congestion window when idle between bursts
net.ipv4.tcp_slow_start_after_idle = 0

# Increased backlog for burst connection handling
net.core.netdev_max_backlog = 5000
net.core.somaxconn = 4096
net.ipv4.tcp_max_syn_backlog = 4096

# Enable MTU probing to avoid fragmentation stalls
net.ipv4.tcp_mtu_probing = 1

# Faster recycling of TIME_WAIT sockets
net.ipv4.tcp_tw_reuse = 1

# NAPI poll budget — process more packets per interrupt cycle
net.core.netdev_budget = 600
net.core.netdev_budget_usecs = 4000

# SACK, window scaling, timestamps (critical for high-throughput)
net.ipv4.tcp_sack = 1
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_dsack = 1
net.ipv4.tcp_timestamps = 1

# Aggressive keepalive (5s detection of dead peers)
net.ipv4.tcp_keepalive_time = 60
net.ipv4.tcp_keepalive_intvl = 10
net.ipv4.tcp_keepalive_probes = 3

# Faster fin timeout for closed connections
net.ipv4.tcp_fin_timeout = 15
```

Apply:
```bash
sudo tee /etc/sysctl.d/99-network-speed.conf << 'EOF'
# ...paste content above...
EOF
sudo sysctl --load /etc/sysctl.d/99-network-speed.conf
```

Persists across reboots automatically via sysctl.d.

### Verification

```bash
# Check all values took effect
sysctl net.core.rmem_max net.core.wmem_max net.core.netdev_budget net.ipv4.tcp_congestion_control

# Measure real throughput improvement with iperf3
# Server (on another machine):
iperf3 -s -D -p 5201

# Client (this machine, run for 10s):
iperf3 -c <target_ip> -p 5201 -t 10

# Look for "Bitrate" in output — see references/speed-test-results.md for baseline numbers
```

## RPS/RFS — Receive Packet Steering (Major Performance Win)

### The problem

By default, all eth0 interrupts land on a single CPU core. On an 8-core i7-6700, CPU 3 handled 162 million interrupts while 7 other cores sat idle. This creates a software bottleneck at 400-500 Mbit/s even with 16MB socket buffers.

### The fix — Spread RX processing across all CPUs

RPS (Receive Packet Steering) distributes packet processing across multiple CPUs at the software interrupt level:

```bash
# Set the CPU mask for all RX queues (ff = all 8 CPUs, adjust per core count)
echo ff | sudo tee /sys/class/net/eth0/queues/rx-0/rps_cpus

# RFS (Receive Flow Steering) — flow table for cache locality
echo 32768 | sudo tee /proc/sys/net/core/rps_sock_flow_entries
echo 2048 | sudo tee /sys/class/net/eth0/queues/rx-0/rps_flow_cnt
```

**CPU mask by core count:**
- 2 cores: `03`
- 4 cores: `0f`
- 6 cores: `3f`
- 8 cores: `ff`
- 12 cores: `fff`
- 16 cores: `ffff`

### Make RPS persistent (systemd service)

RPS is a sysfs write — it doesn't survive reboot. Create a oneshot service:

```bash
sudo tee /etc/systemd/system/rps-network.service > /dev/null << 'SERVICE'
[Unit]
Description=Enable RPS/RFS for eth0 (spread RX across all CPUs)
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'echo ff > /sys/class/net/eth0/queues/rx-0/rps_cpus'
ExecStart=/bin/bash -c 'echo 2048 > /sys/class/net/eth0/queues/rx-0/rps_flow_cnt'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable --now rps-network.service
```

Verify:
```bash
cat /sys/class/net/eth0/queues/rx-0/rps_cpus  # Should show 'ff'
systemctl is-active rps-network.service         # Should show 'active'
```

**Impact from 2026-07-15 session:** kubuntux's wired Tailscale throughput to rabuntu jumped from ~400 Mbit/s to **885 Mbit/s** after enabling RPS/RFS + NAPI budget tuning — nearly saturating gigabit Ethernet through WireGuard.

## Wi-Fi Power Management & Radio Tuning

### The Biggest Wi-Fi Bottleneck: Power Save

Wi-Fi power management causes the radio to enter low-power states between packet bursts, adding 2-10ms of latency per transaction. Disabling it is the single biggest Wi-Fi fix:

```bash
# Check current state
iwconfig wlan0 2>/dev/null | grep "Power Management"

# Disable (immediate effect)
sudo iwconfig wlan0 power off

# Verify
iwconfig wlan0 2>/dev/null | grep "Power Management"  # Should show "off"

# Make permanent via systemd
sudo tee /etc/systemd/system/wifi-perf.service > /dev/null << 'EOF'
[Unit]
Description=Wi-Fi performance tuning
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/iwconfig wlan0 power off
ExecStart=/sbin/ip link set dev wlan0 txqueuelen 10000
RemainAfterExit=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now wifi-perf.service
```

**Impact:** Halved ping in testing (14.8ms → 7.7ms). Throughput +5%.

### TX Queue Length

Default Wi-Fi TX queue length is 1000. Increasing to 10000 improves burst handling:

```bash
sudo ip link set dev wlan0 txqueuelen 10000
```

(Already included in the systemd service above.)

### Interface Name Note

Wi-Fi interface names vary: `wlo1`, `wlan0`, `wlp2s0`. Find yours with `ip link show | grep -E '^[0-9]+: w'` or `iwconfig 2>/dev/null | grep -E '^[a-z0-9]+'`.

### DNS Server Choice

Changing DNS from ISP-default to Cloudflare (1.1.1.1/1.0.0.1) can improve resolution latency:

```bash
sudo resolvectl dns wlan0 1.1.1.1 1.0.0.1 8.8.8.8
```

Test with `resolvectl status` or `dig google.com | grep time`.

## CIFS/Samba Performance Tuning

### Samba Server (kubuntux)

In `/etc/samba/smb.conf` under `[global]`:

```ini
# Performance tuning
use sendfile = yes
aio read size = 16384
aio write size = 16384
read raw = yes
write raw = yes
server signing = disabled
strict rename = yes
socket options = TCP_NODELAY IPTOS_LOWDELAY
```

⚠️ `write cache size = 262144` is UNSUPPORTED on current Samba versions (ignored silently by testparm). Do not set it.

Per-share (`[sharename]`):
```
strict locking = no
oplocks = yes
level2 oplocks = yes
```

Restart: `sudo systemctl restart smbd`

### CIFS Client (lin, macuntu, etc.)

The single biggest improvement is `actimeo` (attribute cache timeout). Default is 1 second — every `stat` call hits the network.

Remount with optimized options:
```bash
sudo mount -t cifs -o actimeo=60,vers=3.0,sec=none,uid=1000,gid=1000,forceuid,forcegid,\
file_mode=0775,dir_mode=0775,soft,nounix,rsize=4194304,wsize=4194304 \
//<server>/<share> /mnt/<mountpoint>
```

**Options explained:**

| Option | Default | Tuned | Effect |
|--------|---------|-------|--------|
| `actimeo` | 1 | 60 | Cache file metadata for 60s instead of 1s. 60x fewer stat calls. **Biggest single win.** |
| `cache` | `strict` | N/A | `loose` and `nocto` not supported on kernel 6.17 — try them on older kernels for aggressive caching |
| `rsize/wsize` | varies | 4MB | Max read/write buffer size |
| `vers=3.0` | varies | 3.0 | SMB 3.0 protocol (modern, encrypted) |
| `soft` | off | on | Soft mounts — don't hang forever on unresponsive server |

**Persistence:** Add to `/etc/fstab`:
```
//100.93.75.87/DEVELOPMENT1 /mnt/development1 cifs actimeo=60,vers=3.0,sec=none,\
uid=1000,gid=1000,forceuid,forcegid,file_mode=0775,dir_mode=0775,soft,nounix,\
rsize=4194304,wsize=4194304 0 0
```

### CIFS client mount gotchas

- `cifs-utils` must be installed (`sudo apt-get install -y cifs-utils`) for `mount.cifs` helper
- `nobrl` (no byte-range locks) not supported on kernel 6.17
- `cache=loose` not supported on kernel 6.17
- `nocto` not supported on kernel 6.17
- Lazy unmount if busy: `sudo umount -l /mnt/point`
- For NFS/CIFS shared across machines, use LOCAL disks for latency-sensitive services (aggregator, git repos) — see the `free-ai-aggregator` skill for the shared-mount gotcha

## Tailscale-Specific Notes

- Tailscale wraps WireGuard; TCP-over-TCP is not an issue since WireGuard uses UDP
- BBR + fq works well through Tailscale's encrypted tunnel
- The main bottleneck on Tailscale links is MTU (1280 default) — MTU probing helps avoid fragmentation stalls
- `tcp_fastopen` saves a round-trip on every new SSH/HTTP connection through Tailscale
- **RPS/RFS is the biggest single win for Tailscale throughput** — wired pairs jumped from ~400 Mbit/s to **885 Mbit/s** after enabling it (nearly saturating gigabit)
- **WiFi clients are the bottleneck**, not TCP tuning — macuntu's WiFi link maxes at ~424 Mbit/s regardless of buffer/IRQ tuning
- See `references/speed-test-results.md` for fleet test data

## Tunnel-Client Notes

When the user asks about "tunnel speed" they likely mean the **OpenAI Secure MCP tunnel-client** (HTTPS to `api.openai.com:443`), not Tailscale/WireGuard. The same TCP stack tuning (BBR, RPS, buffers) applies, but for different reasons:

- **BBR + fq** — handles the long-poll keepalive pattern, keeps cwnd high between poll cycles
- **RPS** — prevents CPU 0 bottlenecks when tunnel poll cycles stack with normal load
- **tcp_slow_start_after_idle=0** — tunnel polls are bursty; prevents cwnd reset
- **TCP fastopen** — saves a round-trip on tunnel reconnect

**Do NOT** optimize WireGuard/Tailscale when the user's concern is the tunnel-client — they're different transport layers. See `references/tunnel-client-optimization-context.md` for the full diagnostic guide and verified numbers.

## Detecting & Removing Unused WireGuard Interfaces

When optimizing network performance, check for stale/abandoned WireGuard tunnels that consume kernel resources:

```bash
# List all WireGuard interfaces
wg show 2>/dev/null || ip link show | grep -E '^[0-9]+: wg'

# Check if managed by systemd
systemctl list-units --all 2>/dev/null | grep wg

# Check routing table entries for wgX interfaces
ip route show table all | grep wg

# Check NetworkManager connections
nmcli connection show 2>/dev/null | grep wg
```

**Cleanup pattern** (run as root):
```bash
# Stop and disable the service
systemctl stop wg-quick@wg0.service
systemctl disable wg-quick@wg0.service

# Delete the interface
ip link delete wg0

# Remove leftover config
rm -f /etc/wireguard/wg0.conf

# Remove stale NetworkManager profile
nmcli connection delete wg0
```

Only Tailscale's `tailscale0` interface should remain. A standalone `wg0` with no active usage is dead weight.

## Fleet Deployment Strategy

When deploying network tuning to multiple machines:
1. Write the config to a file on one machine
2. `scp` to each target
3. `ssh <host> "sudo cp ... && sudo sysctl -p ..."`
4. Verify on each with `sysctl <key>`
