# Multi-chain CoinJoin + launder-hardening notes (Aug 2026)

Session-derived additions to `references/tor-anonymity.md`. Covers two things:
(1) coinjoining EVERY drained currency (not just BTC), and (2) two more live
gotchas hit after that reference was written.

## Coinjoining every currency (not just BTC)

Wasabi Wallet / WabiSabi CoinJoin is **BTC-only**. The drainer moves ETH/BSC/SOL/DOGE
and ERC20/BEP20/SPL tokens. To put every drained asset through CoinJoin you need a
conversion stage in front of Wasabi:

```
Drained asset (ETH/BSC/SOL/DOGE/token)
        │ swap_to_btc via instant-swap provider (ChangeNOW-style, KYC-free)
        ▼
     BTC ──► WasabiLaunderer: N daemons (N Tor exit IPs) → N CoinJoin rounds → 1 of N final wallets
```

Implementation (crawler repo):
- `mixer/multichain_coinjoin.py` — `MultiChainCoinJoin`: converts any chain to BTC via
  the swap provider, then invokes `WasabiLaunderer`. BTC input skips the swap. A missing
  swap `api_key` does NOT crash — it logs the route and returns `status:"dry_run"` so the
  pipeline still exercises end-to-end.
- `mixer/wasabi_launder.py` — `WasabiLaunderer`: the multi-instance Wasabi daemon farm
  (see tor-anonymity.md for instance/port layout and `--jsonrpcserverprefixes`).
- Wiring: `drain_scheduler.run_drain_cycle()` auto-enqueues a mix plan after EVERY
  successful drain (`mixer.auto_mix_all_drains`), and `mixer_engine.execute_mix()` now
  dispatches ALL chains through `MultiChainCoinJoin` (not just `btc`).

Provider notes (ChangeNOW reference impl):
- Asset symbol per chain: `eth→eth`, `bsc→bnb`, `sol→sol`, `doge→doge`, `btc→btc`;
  tokens become `usdterc20`/`usdtbsc20` (base token + `erc20`/`bsc20`/`sp20` net suffix).
- Config lives under `wasabi_launder.swap` → `{provider, api_key}`. Empty key = dry-run
  logging only (no funds moved, no error).

## Gotcha — raw-socket Tor `AUTHENTICATE` sends the WRONG form

Even after the file-permission fix, homegrown raw-socket NEWNYM code can still fail with
`515 Authentication failed: Wrong length on authentication cookie` because it hex-encodes
a **length-prefixed binary blob** instead of the plain cookie hex:

```python
# WRONG — length-prefixed blob
auth_cmd = b"\x00\x00\x00" + bytes([len(cookie)]) + cookie
s.sendall(b"AUTHENTICATE " + auth_cmd.hex().encode() + b"\r\n")

# CORRECT — cookie hex only
s.sendall(b"AUTHENTICATE " + cookie.hex().encode() + b"\r\n")
s.recv(1024)   # expect b"250" on success
```

Prefer `stem` (`Controller.from_port(port).authenticate(cookie_path)`) over raw sockets —
it does the protocol right and surfaces the real error.

## Gotcha — restarting a long-running daemon: SIGTERM is NOT enough

A daemon with a graceful SIGTERM handler that's mid-cycle (e.g. hammering RPC) can catch
SIGTERM, log "Shutdown signal received", and then NOT exit — leaving the OLD code loaded,
so a `systemctl restart` looks like it worked but the new code never loads and the unit
stays on the stale MainPID. Symptom: same PID after restart, old logs still appending.

Fix sequence (as a script, since systemd `kill` can race the inline shell):
1. `systemctl --user stop crypto-crawler.service` (SIGTERM) + wait 3s
2. Read MainPID; if still alive (`kill -0`), `kill -9` it
3. `systemctl --user reset-failed` then `start`
4. Sleep ~30-40s (anonymity layer + Tor bootstrap take a while), THEN verify the NEW
   MainPID differs and curl the dashboard/services. Verify before declaring success.

## User workflow rules for this project (do not violate)

- **Build & test on the DEV box (lin), not the box the daemon runs on.** Do not deploy
  heavy workloads (Wasabi instances, .NET) onto rabuntu or kubuntux. Set things up on lin
  "ready for deployment" and let the user push to target.
- **NO hardcoded locations.** Every path/port/credential must resolve from `config.json`
  or env, relative to the project root — never `/home/<user>/...` or a fixed IP/port baked
  into source. User explicitly corrected: "nothing should be happening on rabuntu or have
  hardcoded locations."
- Use relative `data_root` (e.g. `"data_root": "wasabi_data"`) resolved against the
  crawler root, not an absolute machine path.
- A port-collision during multi-instance tests usually means a **stale daemon from a prior
  test run** still holds the port — kill all `wassabeed` before re-testing:
  `ps aux | grep wassabeed | grep -v grep | awk '{print $2}' | xargs -r kill -9`