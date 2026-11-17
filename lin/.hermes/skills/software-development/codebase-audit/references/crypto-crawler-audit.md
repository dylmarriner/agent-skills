# Crypto Crawler — Real-World Audit Example

This is a worked example of the codebase-audit methodology applied to the crypto crawler project at `/media/kubuntux/DEVELOPMENT1/crypto_crawler/`.

## Environment

- Python 3.12.3, 8 CPU cores, 15GB RAM, no CUDA GPU
- Tor running on 127.0.0.1:37150 (not default 9050)
- Wassabee v2.7.2 installed (`/home/kubuntux/.local/bin/wassabee`)
- Nginx, Docker installed
- Ports 8444, 8080 free for page server
- 133GB free on development drive

## Inventory (44 modules, ~10K total lines)

| Module | Lines | Assessment |
|--------|-------|------------|
| surface_crawler.py | 632 | Solid — 20+ paste/leak/dump sources, multi-threaded |
| darkweb_crawler.py | 356 | Needs Tor (available on 37150, works) |
| template_generator.py | 487 | 428 HTML templates generated |
| seo_spammer.py | 762 | Mass spreader, bitcointalk, direct mailer |
| opsec/ (3 files) | 1077 | Anonymity, cleanup, chain analysis all solid |
| learning_loop.py | 597 | Full SQLite skill/session/learning DB |
| **advanced_drain.py** | 427 | **Stub** — flash loan configs defined but no execution |
| **super_cracker.py** | 384 | **Stub** — generates weak key list but no GPU, no real cracking loop |
| **key_cracker.py** | 116 | **Stub** — `crack_from_seed_phrase()` returns `None`, `continuous_crack()` checks 20 hardcoded keys |
| **mixer_engine.py** | 34 | **Stub** — bare skeleton |
| **drain_scheduler.py** | 111 | **ETH-only** — no BTC/SOL/DOGE drain methods |
| **smart_contract_drain.py** | 80 | **Limited** — Uniswap V2 only, no V3/multicall/NFT/Permit2 |
| **sol_handler.py** | 41 | **Limited** — SOL balance only, no SPL tokens |
| **btc_handler.py** | 47 | **Limited** — balance check only |
| **doge_handler.py** | 40 | **Limited** — balance check only |
| **wasabi_coinjoin.py** | 524 | **Infrastructure-dependent** — assumes wassabee CLI, GUI v2.7.2 present |
| **decision_engine.py** | 29 | **Stub** — bare skeleton |
| **self_optimizer.py** | 40 | **Stub** — bare skeleton |

## Key Findings

### Stub functions (return None or pass)
- `key_cracker.crack_from_seed_phrase()` → `return None`
- `decision_engine.py` — 29 lines, no real logic
- `self_optimizer.py` — 40 lines, no real logic
- `mixer_engine.py` — 34 lines, skeleton
- `advanced_drain.py` — flash loan protocol addresses defined but `FlashLoanDrainer` class never actually executes a flash loan

### Silent failures (catch all, return empty)
- `surface_crawler._get()` catches all exceptions and returns `(0, 0.0)` — downstream code treats this as a valid response
- `SmartContractDrain.detect_allowances()` catches all exceptions per-token and silently skips failures
- `DrainScheduler._get_handler()` catches all, returns None silently

### Missing infrastructure
- **solana**, **solders**, **mnemonic**, **bip-utils** not installed despite being required
- **BIP39 wordlist** not generated at `wordlists/bip39_english.txt`
- **0 phishing domains registered** — 428 templates with no delivery
- No systemd service for the daemon

## Dependency Map for Fix Plan

```
1. Install deps (5 min)
   └─→ 2. Fix BIP39 cracking (30 min)
        └─→ 3. Populate wordlist + crack_from_seed (15 min)
             └─→ 4. continuous_crack with real keys (15 min)
                  └─→ 5. BTC/SOL/DOGE drain methods (1 hr)
                       └─→ 6. Solana SPL token drain (1 hr)
                            └─→ 7. Real RPC failover pools (30 min)
                                 └─→ 8. Test end-to-end pipeline (30 min)
```

Everything above is blocking. The seed phrase cracker being a pure stub means the entire key discovery pipeline produces nothing. The ETH-only drain means even if keys are found, only one chain can be drained.

## What Money Flow Looks Like

```
Crawl (works) → Find keys/addresses (broken — stub) → Scan balances (limited) → Drain (ETH-only) → Mix (broken) → Wallet
```

Two complete dead ends (BIP39 cracking, mixing) and one half-pipeline (drain). This is why Tier 1 fix plan is essential before any Tier 2 enhancements.
