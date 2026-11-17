# Forcing ALL Python Outbound Traffic Through Tor (requests + web3)

Goal: make a Python crawler/drainer 100% Tor-routed — HTTP via `requests` AND
EVM RPC via `web3` — so the host's real IP never touches the crawled sources or
the chains it interacts with. Verified live against a multi-Tor instance on a
remote pi (Debian, Python 3.11 venv) in 2026-08.

## The single most important rule: `socks5h://`, NOT `socks5://`

- `socks5://host:port` — the **local** process resolves DNS, then connects via
  the proxy. The hostname query leaks to the ISP/resolver = DNS leak.
- `socks5h://host:port` — DNS resolution happens **at the proxy (inside Tor)**.
  No local DNS, no ISP-side leak.

Anywhere you hand a proxy to `requests`, use `socks5h://`:
```python
proxies = {"http": "socks5h://127.0.0.1:37150",
           "https": "socks5h://127.0.0.1:37150"}
```
For a normal crawler this alone closes the DNS leak. The `requests` lib ships
socks5h support when PySocks is installed (`pip install pysocks`) — WITHOUT
PySocks installed, every proxy request raises
`Missing dependencies for SOCKS support`. That error means: install PySocks, not
that the proxy is broken.

## Global force-Tor patch (covers requests AND web3)

`requests` and `web3`'s HTTPProvider both build sockets through
`urllib3.util.connection.create_connection`. Monkey-patch that one function and
EVERYTHING (crawlers, RPC, coin-gecko price calls) routes through Tor:

```python
# tor_routing.py
import os, socks, urllib3.util.connection as _u_conn
from urllib3.util.connection import create_connection as _orig_conn

TOR_HOST = os.environ.get("TOR_SOCKS_HOST", "127.0.0.1")
TOR_PORT = int(os.environ.get("TOR_SOCKS_PORT", "37150"))

def _tor_conn(address, timeout=None, source_address=None, socket_options=None):
    host, port = address            # <- address is a TUPLE (host, port)
    return socks.create_connection(
        (host, port),
        timeout=timeout or 30,
        proxy_type=socks.SOCKS5,
        proxy_addr=TOR_HOST,
        proxy_port=TOR_PORT,
        proxy_rdns=True,             # <- keyword is proxy_rdns, NOT rdns
    )

_u_conn.create_connection = _tor_conn
requests.Session.trust_env = False   # ignore HTTP_PROXY/HTTPS_PROXY env leaks
```

Import this module FIRST, before requests/web3 are used anywhere (put the import
at the top of daemon.py / the entry point). Optionally guard the fallback-to-
direct behind an env flag so you never hard-fail when Tor is down.

## Gotchas that WILL bite you

1. **urllib3 passes `create_connection(address, ...)` as a single tuple**, not
   `(host, port)` as two args. Your wrapper must be
   `def _tor_conn(address, timeout=None, ...): host, port = address`.
   If you write `def _tor_conn(host, port, ...)` you get
   `AttributeError: 'tuple' object has no attribute 'startswith'` deep in PySocks.

2. **PySocks kwarg is `proxy_rdns=True`, not `rdns=True`.** Older PySocks
   (Python 3.11 venv) rejects `rdns` with
   `TypeError: create_connection() got an unexpected keyword argument 'rdns'`.
   Newer PySocks on 3.14 accepts both, but `proxy_rdns` is the portable form.

3. **Python version differences are real.** A venv built on 3.12/3.14 is not the
   same as the production host's 3.11 venv. Test the patch ON THE DEPLOY TARGET's
   interpreter, not just locally. (Also: coincurve has no wheel for 3.14 and its
   source build fails — build the project venv on 3.12 where wheels exist.)

4. **Closure variable naming**: if `enforce_global_tor()` defines `_socks_host`
   and the inner `_tor_conn` references `socks_host`, you get a `NameError` at
   call time (not import time). Keep one consistent name inside the closure.

5. **Web3 websocket providers (wss://) are NOT Tor-routable** through SOCKS.
   `Web3.WebsocketProvider` bypasses the urllib3 patch. Either switch the
   mempool/ws monitor to HTTP, or accept that specific connection is a leak.

## Web3-specific RPC routing

`Web3.HTTPProvider` uses urllib3, so the global patch covers it. But if you want
a per-instance Tor Web3 without a global patch, build it with the patched
connection factory temporarily:

```python
def make_tor_web3(rpc_url, timeout=20):
    import socks, urllib3.util.connection as _u_conn
    from urllib3.util.connection import create_connection as _orig
    def _tc(address, timeout=None, source_address=None, socket_options=None):
        h, p = address
        return socks.create_connection((h, p), timeout=timeout or 30,
            proxy_type=socks.SOCKS5, proxy_addr=TOR_HOST, proxy_port=TOR_PORT,
            proxy_rdns=True)
    _u_conn.create_connection = _tc
    try:
        return Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": timeout}))
    finally:
        _u_conn.create_connection = _orig
```

## Tor control cookie permission (NEWNYM rotation fails)

When a systemd user service can't read Tor's control cookie:
- Cookie lives at `CookieAuthFile` from `/etc/tor/torrc`. Default
  `/var/lib/tor/control_auth_cookie` — but `/var/lib/tor` is `drwx--S---`
  `debian-tor:debian-tor`, so even adding the user to the `debian-tor` group does
  NOT help (the parent dir blocks traversal).
- Fix: point `CookieAuthFile /run/tor/control_auth_cookie` in torrc. `/run/tor`
  is `drwxr-sr-x debian-tor:debian-tor` (group-listable). Still `chmod 644` the
  cookie to be safe, because a systemd user service does NOT inherit the
  supplementary group you added to the interactive user until a full re-login /
  `loginctl enable-linger`. Fastest reliable fix: world-readable cookie.
- `stem` control auth: `Controller.from_port(port=...).authenticate("/run/tor/control_auth_cookie")`
  — pass the path explicitly; `authenticate()` with no args uses a default path.

## Verify end-to-end

```bash
# requests through Tor
python3 -c "import requests; print(requests.get('https://check.torproject.org/api/ip', proxies={'http':'socks5h://127.0.0.1:37150','https':'socks5h://127.0.0.1:37150'}, timeout=30).json())"
# => {'IsTor': True, 'IP': '<exit>'}

# web3 through Tor
python3 -c "from opsec.tor_routing import make_tor_web3; w=make_tor_web3('https://eth.drpc.org'); print(w.is_connected(), w.eth.block_number)"
```

The `IsTor: True` from check.torproject.org is the ground-truth that the patch
took effect (not just that the proxy port is open).
