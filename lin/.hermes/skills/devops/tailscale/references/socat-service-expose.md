# Exposing localhost-bound services via socat on Tailscale

Many dev servers bind to `127.0.0.1` by default (security best practice). To make them accessible to other Tailscale nodes:

## Method: socat TCP forwarder

```bash
# Web UI on 127.0.0.1:33301 → expose on 0.0.0.0:8080
socat TCP4-LISTEN:8080,fork,reuseaddr TCP:127.0.0.1:33301 &

# API/daemon on 127.0.0.1:33797 → expose on 0.0.0.0:8081
socat TCP4-LISTEN:8081,fork,reuseaddr TCP:127.0.0.1:33797 &
```

## Important: use TCP4

`socat TCP-LISTEN` defaults to IPv6 which can fail with "Address already in use" if the target process already holds the port on `127.0.0.1`. Always use `TCP4-LISTEN` for explicit IPv4 binding to `0.0.0.0`.

## Verification

```bash
curl -s -o /dev/null -w "%{http_code}" http://<tailscale-ip>:8080
# 200 = working
```

```bash
ss -tlnp | grep socat
# Expect: LISTEN 0 5 0.0.0.0:8080 0.0.0.0:*
```

## Pitfalls

- **Not persistent**: socat processes run in the foreground/background until killed. On reboot, they must be restarted. Use a systemd user service or tmux session for persistence.
- **Port conflicts**: socat cannot bind `0.0.0.0:<port>` if any process (even on `127.0.0.1`) has the IPv6 socket open on `[::]:<port>` with IPV6_V6ONLY=0. Use a different port if "Address already in use" persists.
- **No TLS**: socat forwarders are plain TCP — don't use for production/public access. Acceptable on Tailscale since the network is encrypted at the wire level.
- **Signal handling**: Backgrounded socat doesn't auto-restart if killed. Monitor with `jobs -l` or `ps aux | grep socat`.
