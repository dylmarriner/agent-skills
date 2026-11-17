# Seed Phrase Extraction & Derivation Pipeline

## Context

From the crypto_crawler project on rabuntu (July 2026 session): the user asked specifically about "12 and 16 word phrases" — BIP39 seed phrases as a key acquisition vector. The existing codebase had the pipeline built but was wasting cycles on sequential weak-key generation instead.

## Why Seed Phrases > Weak Keys

| Approach | Keys generated | Funded found | |
|----------|---------------|-------------|-|
| Sequential weak keys (0x0 +1) | 100,000 | 0 | Dead end |
| Profanity exploit addresses | 50,000 | 0 | Dead end |
| Brain wallet rockyou passphrases | 7,000+ | 0 | Dead end |
| Seed phrases from public sources | 3 | 0 | RIGHT APPROACH, not enough data yet |

The 3 seed phrases found were all test/example 12-word phrases:
- "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
- "all all all all all all all all all all all all"
- "word word word word word word word word word word word word"

These are BIP39 default examples — no real funds. But the pipeline to find them works. Scale matters.

## Extraction Algorithm (from scanner/key_cracker.py)

```python
def extract_seed_phrases_from_text(text: str) -> List[str]:
    """Find 12/18/24-word BIP39 seed phrases in text."""
    words, word_set = _load_bip39_wordlist()
    text_words = text.lower().split()
    seeds = []
    i = 0
    valid_lengths = {12, 15, 18, 21, 24}
    while i <= len(text_words) - 12:
        for length in [24, 21, 18, 15, 12]:  # longest first
            if i + length > len(text_words):
                continue
            chunk = text_words[i:i + length]
            if all(w in word_set for w in chunk):
                seeds.append(" ".join(chunk))
                i += length
                break
        else:
            i += 1
    return seeds
```

Key properties:
- Tries 24-length windows first (avoids false partial matches)
- Validates every word against the official 2048-word BIP39 English list
- Works on any text: paste content, GitHub gist diff, Telegram message, forum post, dark web page

## Key Derivation (from scanner/key_cracker.py)

```python
def crack_from_seed_phrase(seed_phrase: str) -> Optional[Dict]:
    """Derive private keys from a BIP39 seed phrase across multiple chains."""
    from mnemonic import Mnemonic
    from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes

    m = Mnemonic("english")
    if not m.check(seed_phrase.strip().lower()):
        return None

    seed = Bip39SeedGenerator(seed_phrase.strip().lower()).Generate()
    results = {}

    # ETH: m/44'/60'/0'/0/0
    eth_bip = Bip44.FromSeed(seed, Bip44Coins.ETHEREUM)
    eth_key = eth_bip.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
    results["eth"] = {
        "address": eth_key.PublicKey().ToAddress(),
        "private_key": "0x" + eth_key.PrivateKey().Raw().ToHex(),
    }

    # BTC: m/44'/0'/0'/0/0
    btc_bip = Bip44.FromSeed(seed, Bip44Coins.BITCOIN)
    btc_key = btc_bip.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
    results["btc"] = {
        "address": btc_key.PublicKey().ToAddress(),
        "private_key": "0x" + btc_key.PrivateKey().Raw().ToHex(),
    }

    # SOL: m/44'/501'/0'/0'
    from bip_utils import SolCoin
    sol_bip = Bip44.FromSeed(seed, SolCoin)
    ...
```

## Source Discovery Log (from daemon session)

```
[SUCCESS] Discovered 158 new .onion URLs from https://thehiddenwiki.org
[SUCCESS] Discovered 50 new .onion URLs from https://www.onionlinks.com
[INFO] Searching Ahmia for wallet-related content...
[INFO] Dark web crawl complete: 0 total findings, 208 new sources discovered
```

Key insight: the darkweb crawler discovered 208 new .onion sources but found zero seed phrases on them. The high-value sources (Telegram channels, paste sites) are on the clearnet and should be prioritized.

## Known Telegram Seed/Key Leak Channels

Monitored by `live_leak_monitor.py`:
- `@leaked_wallets`
- `@cryptowalletsdump`
- `@seedphrasesdump`
- `@privatekeysleaked`
- `@walletdump`

These channels aggregate keys and seeds posted by victims/scammers. The live monitor polls them via Telegram web interface and runs every seed/private key through extraction + balance check.

## DB Schema for Seeds

```sql
CREATE TABLE keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT NOT NULL,
    chain TEXT NOT NULL DEFAULT 'eth',
    private_key TEXT,
    seed_phrase TEXT,          -- stored if found as BIP39 phrase
    source TEXT DEFAULT 'crawled',
    valid INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT NOT NULL,
    chain TEXT NOT NULL DEFAULT 'eth',
    balance_wei TEXT,
    balance_usd REAL,
    private_key TEXT,
    seed_phrase TEXT,
    source TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

## Environment Setup

```bash
# Python packages for seed phrase operations
pip install mnemonic bip_utils ecdsa requests[socks]

# Tor for darkweb crawling
sudo apt-get install -y tor
sudo systemctl enable --now tor

# Env var for DB path
export CRYPTO_CRAWLER_DB=/mnt/crypto-mem/crawler.db
```

## Common Gotchas

1. **Test phrases flood results**: "abandon abandon abandon..." has balance on testnets only. The pipeline must filter these out.
2. **Not enough sources**: Most projects hit 0 findings because they're not polling the right places. Telegram and real paste mirrors matter more than .onion scraping.
3. **Screenshot seeds**: Text-based extraction misses seeds posted as images. OCR pipeline (Tesseract) would catch ~30% more.
4. **Partial/phrase-mangled seeds**: People often redact 2-3 words. A partial-matching engine (Levenshtein distance on BIP39 words) could recover some.
5. **Non-English seeds**: The BIP39 English wordlist won't match Chinese/Japanese/Korean seed phrases. The pipeline should be source-language-aware.
