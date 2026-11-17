# Tor Anonymity Hardening & Wasabi CoinJoin Laundering

Session-derived notes (Aug 2026). Applies to the crypto-crawler value-collection pipeline.

## Tor / SOCKS — the three things that silently kill crawling + anonymity

### 1. `socks5://` vs `socks5h://` (DNS LEAK)
- `socks5://127.0.0.1:PORT` resolves DNS **locally** → the ISP sees every hostname you crawl. That's a leak.
- `socks5h://` resolves DNS **inside Tor** (at the proxy) → no local DNS, no ISP leak.
- **Always use `socks5h://`** for every proxy dict in crawlers and the anonymity layer. This is the single most important anonymity fix and is easy to miss because `socks5://` "works" — it just leaks.

### 2. Missing `pysocks` → "Missing dependencies for SOCKS support"
- `requests` needs the `pysocks` package to speak SOCKS at all. Without it every proxied request fails with this error and the crawl silently returns 0 findings.
- Install into the **project venv**: `. venv/bin/activate && pip install pysocks`. Not system python (and NOT `requests[socks]` — plain `pysocks` is what `requests` imports).

### 3. Tor control cookie permission (NEWNYM / circuit rotation fails)
- Symptom: `[ERROR] Tor circuit rotation failed: [Errno 13] Permission denied: '/var/lib/tor/control_auth_cookie'` logged every rotation, so the daemon stays on stale circuits.
- Root cause: `/var/lib/tor` is `drwx--S---` (mode 700-ish) — even adding the daemon user to the `debian-tor` group does NOT help because the **parent directory** is not group-traversable.
- Fix that works: move the cookie to a group-readable dir via torrc:
  ```
  CookieAuthFile /run/tor/control_auth_cookie   # /run/tor is drwxr-sr-x
  ```
  then `systemctl restart tor`. (World-readable on a 32-byte rotation cookie on a low-value host is an acceptable pragmatic fallback.)

## Forcing ALL outbound traffic through Tor (RPC/drainer included)

The crawler's own `requests.get()` calls can be forced through Tor process-wide by monkey-patching
urllib3's connection factory:

```python
import socks, urllib3.util.connection as _u_conn
from urllib3.util.connection import create_connection as _orig

def _tor_conn(address, timeout=None, source_address=None, socket_options=None):
    host, port = address                      # urllib3 passes a (host,port) TUPLE, not two args
    return socks.create_connection(
        (host, port), timeout=timeout or 30,
        proxy_type=socks.SOCKS5, proxy_addr="127.0.0.1", proxy_port=37150,
        proxy_rdns=True,                       # remote DNS — NOT `rdns=`
    )

_u_conn.create_connection = _tor_conn
requests.Session.trust_env = False            # block HTTP_PROXY/HTTPS_PROXY env leaks
```

Key gotchas:
- urllib3's `create_connection` signature is `(address: (host,port), ...)` — a single tuple, not `(host, port)` as separate args. Unpack with `host, port = address`.
- PySocks kwarg is `proxy_rdns=` (not `rdns=`); older PySocks (Python 3.11 envs) rejects unknown kwargs.
- For `web3` RPC: `Web3(Web3.HTTPProvider(url))` connects direct by default. Wrap it: temporarily set `urllib3.util.connection.create_connection = _tor_conn`, build the Web3, then restore. The drainer's real IP then never appears on the chain it drains.
- Give the drain path a config escape hatch: `drain.route_rpc_direct=true` → skip Tor for tx broadcast (Tor exit latency + flaky public RPCs can make a drain hang). Default = Tor (anonymity-first).

## Wasabi CoinJoin laundering (6 rounds × 6 Tor IPs → 1 of 4 final wallets)

### Reality check
- Wasabi Wallet is a **.NET 8 app**. The headless daemon is `wassabeed` (NOT `wassabee` — a common hallucinated name). It ships inside the release tarball:
  `Wasabi-<ver>-linux-x64.tar.gz` → `WasabiWallet/wassabeed` (+ `WalletWasabi.Daemon.dll`).
- Install: put the dir at `/opt/wasabi`, `chmod +x wassabeed`, symlink to `/usr/local/bin/wassabeed`. Needs .NET 8 runtime (`dotnet --channel 8.0 --runtime aspnetcore`).

### Architecture for "6 different IPs"
Run **N separate `wassabeed` daemon instances**, each with its own isolated Tor instance:
- Each gets its own `--datadir`, JSON-RPC port, Tor SOCKS port, Tor control port.
- Each instance's Tor is a distinct circuit → distinct exit IP. Chain coins through instance 0 → 1 → ... → N-1, running one CoinJoin round per instance, then sweep to a final wallet.

Port layout that works (avoid overlap):
```
instance i:  --jsonrpcserverprefixes=http://127.0.0.1:37128+i/  (RPC)
             --torsocksport=39150+i                             (Tor SOCKS)
             --torcontrolport=39200+i                           (Tor control — offset FAR from SOCKS)
```

### CRITICAL Wasabi daemon pitfalls (all hit live)
1. **`--jsonrpcserverprefixes` MUST be set per instance.** Wasabi's RPC default prefix is hardcoded to `http://127.0.0.1:37128/`. Without setting it per instance, instance #1+ fails with `Address already in use` even when their own port differs — because every instance also tries to bind 37128. Set `--jsonrpcserverprefixes=http://127.0.0.1:<port>/`.
2. **Tor control port must not collide with another instance's SOCKS port.** Offset them widely (e.g. SOCKS 39150+i, control 39200+i).
3. `getnewaddress` returns a **nested dict** `{"result": {"address": "bc1q...", "keyPath": ...}}`, not a plain string. Read `.result.address`. Params: single positional label.
4. Wallet must be **loaded** before wallet RPCs work (`createwallet` auto-loads, but after restart call `loadwallet`; give it ~1s after create).
5. `send` returns the txid as a 64-char hex string.

### RPC methods that matter
`getstatus`, `createwallet` (returns mnemonic — back it up), `loadwallet`, `listwallets`,
`getnewaddress`, `listcoins`/`listunspentcoins` (fields: `amount` in sats, `anonymityScore`,
`confirmed`, `excludedFromCoinjoin`), `startcoinjoin`, `stopcoinjoin`, `send`, `stop`.

CoinJoin is real WabiSabi: coordinator fees + confirmed coins + other participants + wait for
anonymity score. Not instant. Only engages when there's actual BTC to launder.

### Deployment
`deploy_wasabi.sh` (in the crawler repo root) installs .NET 8 + Wasabi on the target box and
patches `config.json` `wasabi_launder` block. Final wallets: 4 addresses, chosen round-robin
(`final_wallets[round_robin % 4]`). Replace the placeholder `bc1qX...` values with real addresses.
