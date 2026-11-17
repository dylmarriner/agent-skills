# Post-Audit Verification — Testing Each Module After Fixing

After implementing the audit's fix plan, systematically verify every changed module independently before declaring success. This prevents "silent stubs" being replaced by "silent regressions."

## Workflow

### 1. Categorize by verified state

After each fix/rewrite, confirm the module passes before moving to the next one:

```python
# Pattern for each module test:
import subprocess, sys

venv = "/path/to/project/venv/bin/python3"
code = """
import sys
sys.path.insert(0, '/path/to/project')
from module.thing import Function

# Test: actual execution
result = Function()
assert result is not None, "expected output"
print(f"VERIFIED: OK — {result}")
"""
r = subprocess.run([venv, "-c", code], capture_output=True, text=True, timeout=30)
print(r.stdout)
if r.returncode != 0:
    print(f"FAILED: {r.stderr[:300]}")
```

### 2. Test types to run per module

| Module type | What to test | Expected |
|-------------|-------------|----------|
| **Data source** (RPC, API) | Connection, balance fetch, response parse | Connected, returns numeric values |
| **Parser/cracker** (BIP39, regex) | Input → output for known test vectors | Deterministic, matches known good values |
| **Drainer** (transfer, swap) | Dry-run execution path, error handling | Returns dry-run hash or None, never crashes |
| **Mixer** (shuffling, hops) | Plan creation, state persistence | Plan produced, state saved and loadable |
| **Infrastructure** (Tor, Nginx) | Port check, traffic test | Service listening, traffic routed |

### 3. Critical: test the data pipeline end-to-end

The most dangerous failure mode is each module passing individually but the chain being broken (A outputs data that B can't parse). After individual tests, trace one complete record:

```
crawl → extract_keys → scan_balance → drain_eth → mixer_plan
```

For each step, check that the output format of the previous step is consumable by the next. Common breaks:
- `str` vs `bytes` vs `hex` for private keys between modules
- Chain name mismatch (`'eth'` vs `'Ethereum'` vs `'ETH'`)
- `int` vs `float` vs `Decimal` for balances
- Address checksum formats (EIP-55 checksummed vs lowercase)

### 4. Verify against known test vectors

For cryptographic or financial logic, use real-world known values:

```python
# BIP39 test vector (abandon...about → known ETH address)
assert crack_from_seed_phrase("abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about")["chains"]["eth"]["address"] == "0x9858EfFD232B4033E47d90003D41EC34EcaEda94"

# SHA256 brain wallet ("password" → known PK)
assert private_key_to_eth_address(sha256(b"password").hex()) == known_address

# Private key → BTC address (key=1 → known BTC address)
assert private_key_to_btc_address("0x0000000000000000000000000000000000000000000000000000000000000001") == "1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm"
```

### 5. Performance baseline

For modules expected to handle large workloads (key cracking, wallet scanning), establish a baseline:

```python
import time
start = time.time()
# run module
elapsed = time.time() - start
# Check: 50K weak keys should scan in < 60s on 8 cores
# Check: 100 ETH addresses should scan balances in < 30s
```

### 6. Commit verification

After all modules pass, the git diff should show only intended changes:

```bash
git diff --stat           # Files changed per module
git diff --stat --staged  # Staged changes
```

Watch for accidental changes to non-target files, especially binary files (`.db`, `.sqlite`) and generated output.

## Pitfalls

- **Don't test with production keys.** Always use known test addresses (Vitalik's ETH addr, genesis BTC addr) for balance checks.
- **Don't assume dry_run=True means "safe."** A bug in the dry-run path that passes real arguments could still cause side effects. Review the dry-run guard in the drainer code.
- **Don't skip verification on "trivial" changes.** A one-line error-handler fix (`return 0, 0.0` instead of `return None`) can break callers that expected a tuple vs Optional.
- **RPC tests are network-dependent.** Run them twice — if the first attempt times out but the second succeeds, it's infrastructure, not code. Note flaky endpoints in the audit.
- **Venv persistence.** If you create a venv for the audit, remember it exists. The project's `main.py` or daemon script may need to be pointed at `./venv/bin/python3` explicitly.
