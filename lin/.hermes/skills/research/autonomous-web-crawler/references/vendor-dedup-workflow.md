# Vendor List Dedup & Tiering Workflow

## When to Use

After running a vendor/product crawl that produces a JSON array of URL+description results, especially when the crawl ran repeatedly and accumulated duplicates, noise, and untrusted entries.

## Workflow

### 1. Read & categorize

```python
from urllib.parse import urlparse
from collections import Counter

with open('results.json') as f:
    data = json.load(f)

# Domain-level grouping
groups = {}
for v in data['vendors']:
    dk = urlparse(v['url']).netloc.lower().replace('www.', '')
    groups.setdefault(dk, []).append(v)
```

### 2. Score entries within each domain

Pick the best entry per domain — prefer root/home URLs, detailed descriptions, etomidate-specific content:

```python
def vendor_score(v):
    url = v.get('url', '')
    desc = v.get('description', '')
    score = 0
    # Prefer root URLs
    path = urlparse(url).path.rstrip('/')
    if not path or path in ['', '/']:
        score += 10
    # Prefer detailed descriptions
    if len(desc) > 50: score += 3
    if len(desc) > 100: score += 2
    # Prefer entries that actually mention the product
    if 'etomidate' in desc.lower(): score += 3
    # Prefer commerce language
    if any(w in desc.lower() for w in ['buy','order','supplier','price']):
        score += 2
    # Penalise long URLs (deep product pages vs root)
    score -= len(url) * 0.01
    return score
```

### 3. Remove noise domains

Maintain separate sets for:
- **trash_domains** — completely irrelevant sites that matched on generic keywords (bestbuy.com, amazon.com, realestate.co.nz, etc.)
- **info_domains** — reference/encyclopedia/news pages that aren't vendors (drugs.com, medscape.com, news articles, research papers, patent databases)

```python
TRASH_DOMAINS = set([...])
INFO_DOMAINS = set([...])

kept = []
for dk, entries in groups.items():
    if dk in TRASH_DOMAINS or dk in INFO_DOMAINS:
        continue
    best = max(entries, key=vendor_score)
    kept.append(best)
```

### 4. Tier by trustworthiness

After dedup, classify each vendor into tiers by its business model:

| Tier | Description | Examples |
|------|-------------|---------|
| **Tier 1** | Legitimate pharma/chemical companies. GMP/USP certified. Real addresses, real products, business registration. Won't sell to individuals without prescription/account. | Sigma-Aldrich, Fisher Scientific, Pfizer, TCI Chemicals, USP Store, Cayman Chemical |
| **Tier 2** | Grey market research chemical vendors. Working e-commerce stores with checkout. Crypto payments only. "For research use" disclaimer. Discreet shipping. No buyer protection. | etomidatestore.com, novapods.net, shroomgarden.co |
| **Tier 3** | Unverified/classified spam. SEO-stuffed classified ad pages, bulletin board comment spam, pages that just reference a seller ID or Threema address. No product, no checkout, no inventory. Likely scams or honeypots. | Polish/Lithuanian/Kyrgyz classifieds, Superprof tutor pages, generic forum spam |

### 5. Build tier1 domain list iteratively

Tier 1 isn't a one-shot — it emerges as you work through the list. Start with well-known companies, then add as you recognise more:

```python
tier1_domains = [
    'sigmaaldrich.com', 'fishersci.com', 'caymanchem.com',
    'hellobio.com', 'pfizerhospitalus.com',
    # ... add as you recognise them
]
```

Run the classification, check for misclassifications (e.g. `cannabisdispensarysshop.com` looks like spam but is actually a real WooCommerce RC vendor → Tier 2), and move entries up or down as needed.

### 6. Output

Write the deduped, tiered file:

```json
{
  "vendors": [...],
  "onion_markets": [...],
  "last_run": "ISO_TIMESTAMP"
}
```

Produce a summary showing:
- Count per tier
- What was removed (trash count, info count, duplicate count)
- Notable findings

## Common pitfalls

- **URL path dedup is not enough** — same vendor has many product pages. Group by domain, score, keep best.
- **Classified spam is still noise** — those Polish/Lithuanian/Kyrgyz classified ad pages with keyword-stuffed descriptions have no product. Don't trust them because they mention your search term.
- **Check user agent** — some classified sites redirect to irrelevant pages based on geo-IP. The description in the crawl result may not match what you see in a browser.
- **Track misclassifications** — every vendor list has edge cases. Note them for the next pass.
- **Tier 1 does not mean "will sell to you"** — it means the company is legitimate. Most require a DEA license, business account, or prescription. Tier 2 is where you'd actually buy from (with risk).
