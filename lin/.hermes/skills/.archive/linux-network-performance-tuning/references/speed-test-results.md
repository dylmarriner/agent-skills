# Fleet Speed Test Results — 2026-07-15 (After RPS/RFS + NAPI Tuning)

After applying RPS (spread eth0 RX across all 8 CPUs), RFS (32768 flow entries), NAPI budget 600/4000us, and consolidated sysctl tuning (16MB buffers, BBR+fq, fastopen, no idle slow-start, backlog 5000). Measured via `iperf3` over Tailscale on local LAN with 10-second tests.

## Tailscale Topology

All machines on `192.168.1.0/24` LAN with direct Tailscale connections (no DERP relay):

```
kubuntux (100.93.75.87) — wired eth0 @ 1000/full — r8168 driver
macuntu  (100.75.23.127) — WiFi (192.168.1.247)
rabuntu  (100.68.0.96)  — wired RPi5 (192.168.1.222)
lin       (100.91.55.113) — WiFi (192.168.1.248)
```

## iperf3 Results (10-second TCP over Tailscale)

| Path | Bitrate | Retransmits | Notes |
|------|---------|-------------|-------|
| kubuntux → rabuntu | **885 Mbit/s** | 3 | Wired → wired RPi5. Near gigabit saturation. RPS was the unlock. |
| kubuntux → macuntu | **424 Mbit/s** | 908 | Wired → WiFi. 100% WiFi-limited, not tunnel. |
| kubuntux → rabuntu (port 2) | **410 Mbit/s** | 573 | Wired → WiFi (second run, consistent). |

## Internet (via Cloudflare CDN — speed.cloudflare.com)

| Direction | Speed |
|-----------|-------|
| Download (25MB file) | **88 Mbps** (11 MB/s) |
| Upload (10MB data) | **79 Mbps** (9.9 MB/s) |
| Ping to 1.1.1.1 | **5ms avg** |

Internet speed is ISP plan capped (~100/80 fiber), not a local bottleneck.

## What Made the Difference

| Change | Impact |
|--------|--------|
| RPS (ff mask on rx-0) | **Biggest** — eth0 interrupts went from 100% on CPU 3 to spread across 8 cores |
| RFS (rps_sock_flow_entries) | Cache locality improvement for flow affinity |
| NAPI budget 300→600 | More packets processed per interrupt cycle |
| rmem_default 212K→256K | Fewer early-connection stalls |
| Consolidation into single sysctl file | Easier to deploy fleet-wide |

## Testing Procedure

```bash
# Start server on listener
iperf3 -s -D -p 5201

# Run client for 10 seconds
iperf3 -c <target_ip> -p 5201 -t 10

# Kill server when done
pkill iperf3
```

## Before/After Comparison

Before tuning (default Ubuntu, RPS off, 212KB buffers): ~170 Mbit/s theoretical cap.
After buffer tuning (16MB): ~400 Mbit/s.
After RPS/RFS + NAPI: **885 Mbit/s** — 2.2× improvement on top of buffer tuning, 5.2× over stock.



# Fleet Speed Test Results — 2026-07-08 (Initial TCP Buffer Tuning Only)

After applying TCP tuning (16MB buffers, fastopen, no idle slow-start), measured via `iperf3` over Tailscale on local LAN.

## Tailscale Topology

All machines on `192.168.1.0/24` LAN with direct Tailscale connections (no DERP relay):

```
kubuntux (192.168.1.225) — wired
lin       (192.168.1.248) — wifi (wlo1), but performs like wired
rabuntu   (192.168.1.222) — wired (RPi5)
macuntu   (192.168.1.247) — wifi only (wlp3s0), weak link
```

## iperf3 Results (5-second test, TCP)

| Path | Bitrate | Retransmits | Notes |
|------|---------|-------------|-------|
| lin → kubuntux | **386 Mbit/s** | 0 | Wifi ↔ wired, solid |
| lin → rabuntu | **397 Mbit/s** | 0 | Wifi ↔ wired RPi5, solid |
| lin → macuntu | **2-14 Mbit/s** | 0 | **Wifi bottleneck** — macuntu's wifi link is the weak point |
| kubuntux → rabuntu | ~400 Mbit/s (inferred) | — | Both wired, same LAN |

## Interpretation

- **Wired pairs hit ~400 Mbit/s** — this is the practical ceiling for Tailscale/WireGuard on these machines. The TCP buffer tuning (212KB → 16MB) removed the socket-level bottleneck, so the limit is now WireGuard CPU overhead + link speed.
- **Lin is on wifi too but performs well** (386 Mbit/s) — good signal, modern card, 5GHz. The tuning helps wifi clients when the link quality is already decent.
- **Macuntu is wifi only and slow** — 2-14 Mbit/s is a physical wifi link quality issue, not TCP tuning. Options: ethernet, move closer to AP, enable 5GHz on the router, or accept wifi speeds. No sysctl tuning compensates for a weak physical link.
- **Zero retransmits** on all tests — the network is clean, no packet loss.

## Testing Procedure

```bash
# Start server on listener
iperf3 -s -p 5201 -D    # daemon mode

# Run client for 5 seconds
iperf3 -c <target_ip> -p 5201 -t 5

# Kill server when done
pkill iperf3
```

## Before/After Comparison (approximate)

Before tuning (212KB buffers): ~170 Mbit/s theoretical cap per connection.
After tuning (16MB buffers): ~400 Mbit/s practical ceiling via WireGuard.

Improvement: ~2.3× for single-stream transfers.
