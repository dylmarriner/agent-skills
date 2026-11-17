# Tunnel-Client Optimization Context

When the user asks to make their network or tunnel faster, they likely mean the **OpenAI Secure MCP tunnel-client** (`tunnel-client run --profile hermes-tools`), not WireGuard/Tailscale tunnels.

## Key Distinction

| User's concern | Actual technology | Optimization target |
|---|---|---|
| "the tunnel" | OpenAI tunnel-client | HTTPS/TCP to `api.openai.com:443` |
| "tailscale" | Tailscale WireGuard | WireGuard UDP tunnel |

The tunnel-client uses **one persistent HTTPS connection** to `162.159.140.245:443` (OpenAI's API endpoint). This is a standard TCP long-poll — NOT a WireGuard tunnel. Optimizing WireGuard throughput has zero effect on tunnel-client performance.

## What Actually Helps the Tunnel-Client

The tunnel-client benefits from generic TCP/HTTPS stack tuning:

- **BBR congestion control** — handles the long-poll's keepalive pattern well, keeps cwnd high between bursts
- **fq qdisc** — pairs with BBR for pacing
- **RPS/RFS** — prevents CPU 0 bottleneck when multiple tunnel poll cycles overlap with normal system load
- **TCP buffer tuning** — 16MB max window handles the long-poll response payload
- **TCP fastopen** — saves a round-trip if the tunnel reconnects
- **tcp_slow_start_after_idle=0** — tunnel polls are bursty; this prevents cwnd reset between polls

## Verified Baseline (kubuntux, 2026-07-15)

| Metric | Value |
|--------|-------|
| OpenAI API latency | 11ms (connect) |
| OpenAI API total | 196ms (first poll round-trip) |
| OpenAI DNS | 8ms → `162.159.140.245` / `172.66.0.243` |
| Active tunnel PID | `tunnel-client` (single persistent connection) |
| Tunnel health | Poller recovers from occasional timeouts |

## What Does NOT Help

- **Tailscale/WireGuard iperf tests** — the tunnel doesn't go through Tailscale
- **Wi-Fi power management tuning** — kubuntux is wired (eth0)
- **CIFS/Samba tuning** — only relevant for file sharing
- **MTU tuning** — standard 1500 (eth0) is fine for HTTPS

## When to Optimize Each Target

| User says | Focus on | Do NOT |
|---|---|---|
| "tunnel is slow" | TCP stack: BBR, RPS, buffers, fastopen | WireGuard iperf tests |
| "tailscale is slow" | RPS first, then BBR, then MTU | Tunnel-client health checks |
| "network is slow" | Internet speed test first, then TCP stack | Both at once — isolate |
| "internet is slow" | ISP speed test, DNS, then TCP stack | Tunnel/WireGuard tuning |

## Quick Diagnostic Commands

```bash
# Tunnel health
ps aux | grep tunnel-client
curl -s https://api.openai.com/v1/models -o /dev/null -w "OpenAI latency: %{time_connect}s\\n" --max-time 10

# TCP stack
sysctl net.ipv4.tcp_congestion_control net.core.default_qdisc
cat /sys/class/net/eth0/queues/rx-0/rps_cpus

# Internet speed (Cloudflare)
curl -s -o /dev/null -w "DL: %{speed_download} B/s\\n" --max-time 15 'https://speed.cloudflare.com/__down?bytes=25000000'
```
