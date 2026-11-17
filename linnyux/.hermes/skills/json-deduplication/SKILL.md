---
name: json-deduplication
description: Deduplicate JSON arrays by grouping on a key field, scoring entries, and removing noise. Handles crawler/scraper output, vendor lists, and any dataset where the same entity appears under multiple URLs.
allowed-tools: Read Grep Glob Bash Write ExecuteCode
---

# JSON Deduplication

## When to use this skill

- **Crawler output cleanup**: Deduping scraped vendor/product data where the same entity appears across multiple URLs
- **Search harvest noise removal**: Removing irrelevant search results (trash domains, info/reference pages) from harvested datasets
- **Same-domain merging**: Merging multiple product/category pages from the same vendor into a single representative entry
- **Data quality audit**: Finding and removing tracker URLs, SEO spam, and false positives

## Workflow

### Step 1: Load and analyze the data

```python
import json
from urllib.parse import urlparse
from collections import Counter

with open('input.json') as f:
    data = json.load(f)

items = data['items']  # adjust key name
print(f"Total entries: {len(items)}")

# Count unique URLs
urls = [item['url'] for item in items if item.get('url')]
print(f"Exact URL duplicates: {len(urls) - len(set(urls))}")

# Count domains
domains = Counter()
for item in items:
    if item.get('url'):
        d = urlparse(item['url']).netloc.lower()
        domains[d] += 1

print("Domains with multiple entries:")
for d, c in domains.most_common():
    if c > 1:
        print(f"  {d}: {c}")
```

### Step 2: Define noise filters

Identify categories of entries to remove:

| Category | Examples | Action |
|----------|----------|--------|
| Tracker noise | `/clev?event=...`, analytics URLs | Remove |
| Trash noise | bestbuy.com, amazon.com, realestate.co.nz | Remove (false matches) |
| Info/reference | drugs.com, medscape, news articles | Remove (not vendors) |
| Classified spam | ogloszenia.*, elenta.lt, SEO-stuffed listings | Keep 1 per domain |
| Real entries | Vendor shops, API suppliers, product pages | Keep, merge by domain |

```python
trash_domains = {'bestbuy.com', 'realestate.co.nz', ...}
info_domains = {'drugs.com', 'medscape.com', ...}
```

### Step 3: Group by domain, score best entry

```python
def is_root_url(url):
    # Root/homepage URLs are preferred
    if not url:
        return False
    path = urlparse(url).path.rstrip('/')
    return not path or path in ['', '/', '/index.html', '/index.php', '/home']

def score(v):
    """Higher = better entry to keep"""
    url = v.get('url', '')
    desc = v.get('description', '')
    score = 0
    if is_root_url(url):
        score += 10
    if len(desc) > 50:
        score += 3
    if 'etomidate' in desc.lower():  # or whatever your domain keyword is
        score += 3
    # Shorter URLs are better (root > deep product page)
    score -= len(url) * 0.01
    return score

# Group by domain
groups = {}
for item in items:
    dk = urlparse(item['url']).netloc.lower()
    dk = dk.replace('www.', '')
    if dk not in groups:
        groups[dk] = []
    groups[dk].append(item)

# Pick best per domain
kept = []
for dk, entries in groups.items():
    if dk in trash_domains or dk in info_domains:
        continue
    best = max(entries, key=score)
    kept.append(best)
```

### Step 4: Re-serialize

```python
output = {
    "items": sorted(kept, key=lambda v: urlparse(v['url']).netloc.lower()),
    "metadata": data.get('metadata', {}),
    "last_run": data.get('last_run', '')
}

with open('output.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"{len(items)} → {len(kept)} ({len(items)-len(kept)} removed)")
```

## Best practices

1. **Always preserve `last_run` and metadata** — don't lose the crawl timestamp
2. **Check each removal category** — verify a sample before bulk removal
3. **Keep onion/restricted-market entries separate** — they're in a different array, don't dedup against clearnet
4. **Root URL preference** — when merging product pages, keep the homepage or main store URL, not a deep product link
5. **Domain-key normalization** — strip `www.` to group `example.com` with `www.example.com`
6. **Descriptive scoring** — longer descriptions with relevant keywords score higher

## Pitfalls

- **Search engine noise** — queries with generic keywords (buy, order, price) return false positives from real estate, electronics, crypto exchanges. Must filter by domain, not just title.
- **Reversible dedup** — backup the original before running. If you over-filter, recovery is painful.
- **Info/reference blur** — medical info sites (drugs.com, Medscape) explain the substance but don't sell it. They look relevant but aren't vendors.
- **SEO spam** — classified sites with stuffed keywords (elenta.lt, massoq.com, autobaza.kg) appear to be vendors but are just spam pages with etomidate in the description. Keep them as leads but flag them as low-quality.

## References

- `references/vendor-dedup-etomidate.md` — full session transcript for the etomidate vendors dedup

## When NOT to use this skill

- **Structured database dedup** (SQL UNIQUE constraints, ON CONFLICT) — use database-native dedup
- **Hash-based file dedup** — use `fdupes` or `jdupes`
- **Simple Python `set()` dedup** — use when entries have exact-match keys and no grouping needed
