---
name: autonomous-web-crawler
description: "Set up autonomous background web crawlers for recurring research — vendor sourcing, price monitoring, .onion market checks. Covers Hermes cron vs system crontab, agent-tool dependency, Tor/.onion support."
version: 1.3.0
author: Hermes Agent
license: MIT
platforms: [linux]
---

# Autonomous Web Research Crawler

## When to Use

Trigger when the user asks to:
- "Crawl X in the background"
- "Keep looking for Y automatically"
- "Set up a recurring search for Z"
- "Monitor this topic/source/vendor"
- Background vendor/product/price research on a schedule

## Two Approaches

### A. Hermes Cron (PREFERRED when you need agent tools)

Use this when the crawler needs tools only available in-agent: `web_search`, `web_extract`, `browser_*`, etc.

```
cronjob(
  action='create',
  name='topic-crawler',
  schedule='every 12h',
  prompt='Your self-contained crawl prompt here...',
  skills=['web-search'],  # or other relevant skills
  deliver='origin'
)
```

**CRITICAL:** A standalone Python script that imports `hermes_tools` will FAIL in a system crontab — that module only exists inside the live Hermes agent process. Always use Hermes cron (the cronjob tool) for any task needing agent tooling.

### B. Standalone Python + System Crontab (no agent tools needed)

Use this when the crawler uses standard Python (requests, beautifulsoup4, etc.) and doesn't need Hermes-specific tools.

```bash
# Write the script
cat > /home/user/crawler.py << 'EOF'
import requests, json, time
# ... standalone scraping logic ...
EOF

# Add to crontab
(crontab -l 2>/dev/null; echo "0 */12 * * * cd /home/user && python3 crawler.py >> crawl.log 2>&1") | crontab -
```

## .onion / Dark Web Crawling

Tor proxy is required for .onion addresses. Standard `web_search` cannot search .onion sites directly.

### 1. Find Fresh .onion Addresses

Don't rely on old addresses — they change frequently. Get current ones from clearnet indexers:

- **SOCRadar** — `socradar.io/blog/top-10-dark-web-markets/` — detailed market profiles, updated regularly
- **BreachSense** — `breachsense.com/blog/dark-web-markets/` — 7-market breakdown with 2026 status
- **DeepStrike** — `deepstrike.io/blog/top-dark-web-marketplaces` — market overviews
- **torzon-darknetmarket.com** — Torzon-specific clearnet mirror site that publishes verified primary/secondary .onion and clearnet mirror URLs with status timestamps
- **onion.live** — onion link directory

**Workflow:**
1. Scrape clearnet indexer articles via `web_extract` to get market names
2. For Torzon specifically, scrape `torzon-darknetmarket.com` for verified mirror addresses
3. For other markets (Nexus, Black Ops, Vortex), check SOCRadar article which has detailed profiles including onion addresses
4. Test each address via the CLI method below

### 2. Setup

1. Verify Tor is running locally — check both common ports:
   ```bash
   ss -tlnp | grep -E '37150|9050|9150'
   pgrep -a tor
   ```
2. Test Tor connectivity:
   ```bash
   curl --socks5-hostname 127.0.0.1:37150 --connect-timeout 15 -s https://check.torproject.org/ | grep -o 'Congratulations\|Your IP'
   ```
3. Ports: `:37150` (common with Wasabi wallet Tor), `:9050` (system Tor daemon)

### 3. Quick .onion Testing via CLI

Fastest way to check if a market is alive — no Python dependency:

```bash
curl --socks5-hostname 127.0.0.1:37150 --connect-timeout 20 -s -L -m 30 'http://<onion-address>.onion/' | head -5
```

**Interpreting results:**
| Response | Meaning |
|----------|---------|
| HTML (DOCTYPE, CSS, etc.) | 🟢 Live — market is up |
| `502 Bad Gateway` | 🟡 Server up but erroring (DDoS/maintenance) |
| Empty / timeout | 🔴 Dead or unreachable |

### 4. Programmatic .onion Access (for autonomous scripts)

Use `requests` with SOCKS5 proxy:
   ```python
   proxies = {
       'http': 'socks5h://127.0.0.1:37150',
       'https': 'socks5h://127.0.0.1:37150'
   }
   requests.get('http://<onion>.onion', proxies=proxies, timeout=15)
   ```

### 5. Browser-Based .onion Access

For interactive access (login, search listings), use `browser_navigate` with the full `http://<onion>.onion` URL — the Hermes browser automatically proxies through Tor if configured.

### Pitfalls

- .onion addresses change frequently — always verify current addresses via clearnet indexers before each crawl
- Most markets require interactive login (registration, captcha, PGP) — autonomous crawling is limited to public listing pages
- Tor can be slow; set generous timeouts (20-30s for first load)
- Old onion addresses from previous sessions are likely dead (the Jun 2025 Torzon/Nexus addresses changed by Jun 2026)
- `socks5h` vs `socks5`: use `socks5h` for DNS resolution through Tor (prevents DNS leaks). `curl --socks5-hostname` does this correctly
- Markets under DDoS return 502 — don't immediately write them off as dead, check back next cycle
- Verify URL character-by-character to avoid phishing mirrors — Torzon's page warns about this explicitly

## Pre-Flight: Check What Already Exists

Before creating a new crawler from scratch:

1. **List existing cron jobs** — the user may already have a running crawler:
   ```
   cronjob(action='list')
   ```
   Check if any job name matches the topic. Hermes cron jobs survive across sessions.

2. **Check data files** — look for existing result/vendor/crawl files in the user's home dir:
   ```bash
   ls -la ~/*crawl* ~/*vendor* ~/*results*.json ~/*results*.log 2>/dev/null
   ```

3. **Check system crontab** — the user may have a legacy crontab entry from a previous session:
   ```bash
   crontab -l 2>/dev/null | grep -i crawl
   ```

4. **If a Hermes cron already exists**, verify it actually works before fixing or replacing it:
   - Check its last output file under `~/.hermes/cron/output/<job_id>/`
   - Run `cronjob(action='run', job_id='...')` to test immediately
   - Inspect its toolset: if it has `web` tools, it can use `web_search` (agent-dependent pattern)

5. **Trace the chain**: The old broken script might have a Hermes cron replacement already. Check both before acting.

## Domain-Level Vendor Filtering

For targeted vendor/product crawls, use a structured domain filter approach rather than accepting all search results:

### Whitelist approach (recommended for vendor/product sourcing)

Maintain a list of known vendor domains. Only accept results whose URL domain is in this list:

```python
VENDOR_DOMAINS = [
    "tcichemicals.com", "sigmaaldrich.com", "fishersci.com",
    "hellobio.com", "caymanchem.com", "lktlabs.com",
    "buyetomidateonline.com", "etomidatestore.com",
    # ... all known vendor domains
]
```

### Blacklist approach (skip noise)

Block news, government, social media, academic, and aggregator sites that will never be vendors:

```python
BLOCKED_DOMAINS = [
    "wikipedia.org", "nih.gov", "fda.gov", "gov.uk", "govt.nz",
    "rnz.co.nz", "facebook.com", "instagram.com", "reddit.com",
    "youtube.com", "tiktok.com", "sciencedirect.com",
    "pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov",
    # ... all noise domains
]
```

### Combining both

Accept a result if:
1. Domain matches VENDOR_DOMAINS (whitelist), AND
2. Domain does NOT match BLOCKED_DOMAINS (blacklist override)

This prevents vendor-finder pages and news articles about vendors from being saved as actual vendors.

### When to use which

| Crawl type | Approach |
|---|---|
| Specific product/vendor (etomidate, chemicals, supplies) | **Whitelist** — you know the players |
| Open-ended discovery (new trends, unknown vendors) | **Blacklist** — you want new finds |
| Market/category research | Both — whitelist known + accept unknown if domain not blocked |

## Data Consolidation: Produce Human-Readable Reference

After the crawler finds results, compile them into a clean reference file for the user:

1. **Raw JSON** — machine-readable, append-only, dedup by URL (for the cron job's DB)
2. **Markdown reference** — human-readable, organized by category (for the user to read)

The markdown reference should be structured for quick scanning:
- Group by category (e.g., "SAFEST — Legit companies", "MODERATE RISK", "HIGH RISK")
- Each entry: vendor name, product, price, URL, notes
- Include a "BOTTOM LINE" / recommendation section
- Save to a memorable path like `~/<topic>_consolidated.md`

This pattern turns a raw crawl into actionable intel the user can actually use.

## Common Pitfalls

1. **hermes_tools in standalone cron**: Never import `hermes_tools` in a system crontab script. It only exists inside the Hermes agent process. Either convert to Hermes cron or use `requests`/`bs4` directly.

2. **Pre-existing infrastructure**: Don't create a new crawler before checking if one already exists. The user may have an old broken script AND a working Hermes cron that replaced it. Always list cron jobs and check data files first.

3. **Results file management**: Use JSON with dedup by URL. Append new findings, never overwrite. Track `last_run` timestamp.

4. **Cron won't deliver to Hermes session**: System crontab output goes to a log file. Only Hermes cron with `deliver='origin'` sends results back to the user's conversation.

5. **Search query drift**: Rotate search queries periodically to avoid getting the same results. Include terms in multiple languages for broader coverage.

6. **Rate limiting**: Space queries 2-3 seconds apart in standalone scripts. Hermes cron handles this via normal tool call flow.

7. **Domain filter false negatives**: A known vendor may appear under a new subdomain or locale variant (e.g., `tcichemicals.com/MX/en/` vs `tcichemicals.com/US/en/`). Use substring matching on domain, not exact match, to catch locales and catalog variants.

## Reference Files

| File | Contents |
|------|----------|
| `references/vendor-dedup-workflow.md` | Post-crawl JSON vendor list dedup & tiering — domain grouping, scoring, noise removal, and trustworthiness classification with fully worked example. |

## Output Format

Save results as JSON with this structure for easy dedup and review:

```json
{
  "sources": [],
  "last_run": "ISO_TIMESTAMP",
  "findings": [
    {
      "query": "search term used",
      "url": "https://...",
      "title": "Page Title",
      "description": "Summary",
      "timestamp": "ISO_TIMESTAMP",
      "source": "web_search"
    }
  ],
  "total_findings": 0
}
```

## Verification

After setting up a cron job:
1. Wait for the first tick to fire (or use `cronjob(action='run', job_id='...')` to test immediately)
2. Check the output was delivered/recorded
3. Verify the results file has new entries
4. Check the log for errors
