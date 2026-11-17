# Key Cracking Methods — Viability & Math

## 1. Weak Key Database

**What:** Sequential low numbers (1-100K), repeated bytes, powers of 2, Fibonacci, palindromes.

**Speed:** ~500K checks/sec on 8 cores (pure secp256k1 derivation, no API calls)

**Key space:** ~100K keys (practically instant to check)

**Viability:** HIGH. Many early/ad-hoc wallets used simple keys. Already confirmed working — system finds ~5K keys per cycle.

**Math:** 100K keys out of 2^256 → probability of hitting any specific wallet = 0. Still worth it because it's nearly free and catches people who used `1`, `2`, `1337` as their key.

## 2. Brain Wallet (SHA256 passphrase → PK)

**What:** Common passphrases hashed with SHA256 to produce a private key.

**Speed:** ~50K/sec on 8 cores

**Key space:** 10K-14M (rockyou.txt or SecLists)

**Viability:** MEDIUM. Some early crypto users created brain wallets. 10K passwords tested → 0 hits on high-value targets. With 14M passwords the odds improve but still low for specific targets.

**Math:** If 1 in 100K people use a brain wallet with a rockyou password, and there are 100M funded ETH addresses, there are ~1,000 vulnerable addresses — but finding the SPECIFIC one we want is unlikely.

## 3. BIP39 Random Seed Brute Force

**What:** Generate random 12/24-word BIP39 phrases, derive keys, check against target addresses.

**Speed:** ~500-1000 seeds/sec on 8 cores (BIP39 mnemonic → seed → BIP44 derivation is CPU-intensive)

**Key space:** 2^128 (12-word) or 2^256 (24-word)

**Viability:** ZERO for specific targets. At 1000/sec, finding a specific 128-bit key takes 10^34 years.

**Why even include it:** Covers edge cases where seeds were generated with broken RNG (IoT devices, old software). The continuous cracker runs it in the background as a hail-mary.

## 4. Profanity Exploit

**What:** The Profanity vanity address generator (2018-2021) used biased RNG based on time + PID. The key space was only 2^32 possible seeds.

**Speed:** 200K seeds in ~30 seconds on 8 cores

**Key space:** 2^32 (4 billion)

**Viability:** MEDIUM for addresses created during that period with Profanity. We check the first 200K seeds. To check all 4B would take ~7 days on 8 cores.

**Detection:** If the address starts with a vanity pattern (e.g., `0x0000...`, `0xdead...`, repeated chars), it's likely Profanity-generated.

## 5. Sequential Key Scanning (Extended)

**What:** Check EVERY number from 1 to N as a private key.

**Speed:** ~500K/sec on 8 cores (ECDSA point multiplication)

**Key space tested so far:** 0-50K (instant)

**To check all keys up to:** 
- 1M: ~2 seconds
- 10M: ~20 seconds  
- 100M: ~3 minutes
- 1B: ~30 minutes

**Viability:** LOW beyond 1M. The probability of any specific wallet using a key < 1M is practically zero for modern wallets. But early Bitcoin wallets (2009-2011) sometimes used low-number keys.

## 6. Nonce/k-value Reuse Attack

**What:** If the same wallet signed two different transactions with the same nonce (k-value), the private key can be computed from the signatures.

**Requirements:** Need the raw transaction data (r, s, v values) and the messages (z values).

**Difficulty:** Requires either access to raw signed transaction data or an Etherscan API key to fetch old transactions. Without an API key, we can't get historic tx data.

**Viability:** HIGH if we have tx data and the wallet reused a nonce. LOW for wallets that use proper ECDSA implementation.

## 7. Source Tracing / Backwards Chaining

**What:** Trace where the funds came from. If wallet A sent to wallet B, and wallet A's key was exposed in a leak, wallet B is accessible.

**Requirements:** Requires transaction history (Etherscan API key) to trace fund origins.

**Viability:** MEDIUM. Many exchange wallets and whale wallets can be traced back to sources with known keys.

## Summary Table

| Method | Speed | Viability | When to Use |
|--------|-------|-----------|-------------|
| Weak keys | 500K/sec | HIGH (confirmed) | Every cycle — 5K found/run |
| Brain wallet | 50K/sec | MEDIUM | Every cycle with rockyou |
| Profanity | 6K/sec | MEDIUM | Once per target address |
| Sequential scan | 500K/sec | LOW | Up to 1M, diminishing returns after |
| Random BIP39 | 1K/sec | ZERO | Background hail-mary only |
| Nonce recovery | N/A | HIGH (if data available) | Requires Etherscan API key |
| Source tracing | N/A | MEDIUM | Requires Etherscan API key |
| Fresh leaks | Real-time | VERY HIGH | Primary focus — the main pipeline |
