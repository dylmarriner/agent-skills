# Pi Unreachable — Relay-Only Tailscale Connection

## Scenario

The Pi at **100.68.0.96** (hostname `rabuntu`) appears in `tailscale status` as:

```
100.68.0.96  rabuntu  inhumanekiller22@  linux  active; relay "hkg", tx 1258499000 rx 171892192
```

Despite being "active" via a relay in Hong Kong, ALL services are unreachable from machines outside the Pi's local network:

| Service | Port | Result |
|---------|------|--------|
| SSH | 22 | Connection timed out |
| SMB/CIFS | 445 | Connection timed out |
| HTTP | 80 | Connection timed out |
| Tailscale ping | — | All pings timed out (`--until-direct=false` also fails) |

## Diagnostic Results

1. **Tailscale status** → `active; relay "hkg"` — the Pi has outbound Tailscale connectivity via relay, but no direct path exists
2. **Tailscale ping** → all 3 pings timed out, even with `--until-direct=false`
3. **Port probes** → SSH (22), SMB (445), HTTP (80) all time out from the connecting machine
4. **Existing CIFS mount** (`/mnt/pivideos` using `soft` option) hangs indefinitely when the Pi is unreachable
5. **Jump host attempts** → SSH via `root@100.102.4.39` and `macuntu@100.75.23.127` also fail (both show `relay "hkg"` with no direct path)

## Conclusion

When a Pi shows `active; relay "<city>"` but ALL ports time out and all jump hosts also fail:
- The Pi has a Tailscale control connection (it's registered and heartbeating) but there is no viable traffic path
- This typically means the Pi is behind a very restrictive NAT where only the initial DERP relay registration works, but subsequent data-plane connections fail
- **Possible causes**: power-off, network interface down, OS hang (e.g. exFAT I/O freeze), or a firewall that blocks all inbound even over Tailscale relay
- **Only resolution**: physical or local-network access to the Pi to diagnose the root cause

## Next Steps When Status Improves

When the Pi becomes reachable again (e.g. the user reboots it or fixes the network):

```bash
# First, verify it's back
tailscale ping -c 2 100.68.0.96

# Then SSH and check what went wrong
ssh rabuntu@100.68.0.96 "
  uptime;
  dmesg | tail -30;
  journalctl -p err --since '24 hours ago' | tail -30;
  systemctl status ssh --no-pager;
  df -h
"
```
