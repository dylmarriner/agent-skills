# Tor / .onion Dark Web Investigation — Command Reference

## Check if Tor is Running

```
ss -tlnp | grep -E '37150|9050|9150'
netstat -tlnp 2>/dev/null | grep -E '37150|9050|9150'
pgrep -a tor
```

- **`:37150`** — Wasabi wallet Tor instance (often on desktop)
- **`:9050`** — System Tor (default, tor package)
- **`:9150`** — Tor Browser Bundle

## Verify Tor is Functional

```
curl --socks5-hostname 127.0.0.1:37150 --connect-timeout 10 -s \
  https://check.torproject.org/ | grep -o 'Congratulations\|Your IP\|This browser'
```

Returning "Congratulations" = Tor is working.

## Test a .onion Address

```
curl --socks5-hostname 127.0.0.1:37150 --connect-timeout 20 -s -L -m 30 \
  'http://<56-char-onion-id>.onion/' 2>&1 | head -30
```

**Parameters:**
- `--socks5-hostname` — Route DNS + request through SOCKS5 (handles .onion hostname resolution)
- `--connect-timeout 20` — Wait up to 20s for connection (Tor is slow)
- `-m 30` — Max total time 30s
- `-L` — Follow redirects
- `-s` — Silent (no progress meter)

### Interpreting Results

| Response | Meaning |
|----------|---------|
| Full HTML page rendered (CSS, favicon, forms) | Market is **LIVE** |
| Minimal HTML (just a title or meta tags) | Site responds, likely behind login/captcha |
| Empty output + clean exit code | Service exists but returns nothing — may require specific path |
| curl: (28) Connection timeout | Dead or very slow node |
| curl: (7) Failed to connect | Address is dead, wrong port, or service down |
| curl: (6) Could not resolve host | Invalid .onion address (check for typos) |
| HTTP 301/302 redirect | Market may have moved — follow redirects with `-L` |
| HTTP 502/503 | Server up but erroring (DDoS, maintenance, overload) |
| HTTP 200 + captcha HTML | Live but gated — requires browser interaction |

## Finding Current .onion Addresses — Clearnet Indexers

Don't rely on old addresses — they change frequently (market reboots, exit scams, seizures). Get current ones from clearnet:

### Primary Sources

1. **dark.fail** — `https://dark.fail/` — the canonical .onion uptime tracker. PGP-verified addresses. Shows online/offline status per site. Homepage has an alert banner when major markets are seized.

   **Usage:**
   ```bash
   # Get market addresses from dark.fail
   curl -sL "https://dark.fail/" -H "User-Agent: Mozilla/5.0" | \
     grep -oP 'href="[^"]*\.onion[^"]*' | cut -d'"' -f2
   ```
   
   **Limitation:** dark.fail's status data (online/offline labels) is rendered via CSS classes, not text. The clearnet site shows all addresses but not their live status. Visit the .onion version for accurate uptime:
   `darkfailenbsdla5mal2mxn2uz66od5vtzd5qozslagrfzachha3f3id.onion`

2. **tor.taxi** — `https://tor.taxi/` — darknet directory with clickable .onion links organized by category (Markets, Forums, Exchanges). Clean HTML, easy to scrape.

   **Usage:**
   ```bash
   # Extract all .onion links from tor.taxi
   curl -sL "https://tor.taxi/" -H "User-Agent: Mozilla/5.0" | \
     grep -oP 'http://[a-z2-7]{56}\.onion[^"]*'
   ```
   
   tor.taxi shows market names as visible text labels with links to their .onion addresses. Parsing the page source yields both the display name and the onion address.

### Secondary (blog/research) Sources

Sources that often list current addresses contextually:
- `socradar.io/blog/top-10-dark-web-markets/` — detailed market profiles
- `breachsense.com/blog/dark-web-markets/` — 7-market breakdown with status
- `deepstrike.io/blog/top-dark-web-marketplaces` — market overviews
- `blog.globalledger.io` — darknet market research
- `torzon-darknetmarket.com` — Torzon-specific clearnet mirror

### Clearnet Search Queries

```bash
web_search query="TorZon market .onion link 2026"
web_search query="darknet market working onion addresses 2026"
web_search query="top dark web markets 2026"
web_search query="bohemia market onion address 2026"
web_search query="incognito market darknet link"
```

**When web_search fails** (credit exhausted, blocked), use curl directly against Bing or other engines, or scrape the indexers listed above.

### Extracting .onion Addresses from Any HTML

```bash
# Extract v3 .onion addresses (56-char base32)
grep -oP '[a-z2-7]{56}\.onion' page.html

# Extract any .onion addresses
grep -oP '[a-z2-7]{16,56}\.onion' page.html
```

## Known Dark Web Markets (as of July 2026)

| Market | Onion Address | Status | Notes |
|--------|--------------|--------|-------|
| **Torzon** | 7hlducio2a57if4vk5yt7g63cbs42dffztcmkyjjrb7bmdy5iuuyi7qd.onion | 301 redirect, empty response | Possibly alive behind login gate or redirect loop |
| **Nexus Market** | nexusb2l7hog66bnzz5msrz4m5qxj7jbi7aah3r65uzydy5mew2fu3id.onion | Captcha (200 OK) | Accessible but behind Cloudflare verification. Needs manual browser |
| **Drughub** | drughub666py6fgnml5kmxa7fva5noppkf6wkai4fwwvzwt4rz645aqd.onion | 503 Service Unavailable | May be overloaded or down for maintenance |
| **Black Ops** | blackops527cggb6ybayggx3bjt24xz32rotdugs6ikejxdiik6dyiid.onion | Timed out (dead) | Address may have changed or market shut down |
| **Vortex** | mq7ozbnrqdjc6cof3yakegs44kmo6vl3ajcyzdeya3zjtmi65jtmwqid.onion | Cannot resolve (dead) | Hostname invalid, market likely defunct |
| **Bohemia** | bohemiabk5kmsn2q4fhb2qw3sz2npiqcbfvv7jofrhi5m4ynyvne5wid.onion | Unknown | Major general market. Successor to several others. Untested this session |
| **Incognito** | incognitordm7fbkcoxkqjqt2e4qattkp5mdiaob4igovqrgcnljgyd.onion | Unknown | Large general DNM. Untested this session |
| **Dark Matter** | darkmat3kdxestusl437urshpsravq7oqb7t3m36u2l62vnmmldzdmid.onion | Unknown | Listed on tor.taxi as active market |
| **Flugsvamp 4.0** | flugsvampqwm53dxuv2wbb7g37w4qyq3k4f4qfewqbxzwk57zczcbid.onion | Unknown | Swedish, primarily EUR vendors |
| **Kraken** | krakenmarketqd25hgw2otba5m5dgqyripxcpmgmf6tdjqrw6y3d56yd.onion | Unknown | Russian-language market |
| **Blacksprut** | blacksprut7ej6it3nkgg2oqbvysw5nr3fe7kq2jq57q6ty4paqhyd.onion | Unknown | Large Russian market |
| **MEGA (MGM Grand)** | mega4m57llcmkasa5ilvq2iil7fwqzt4hwhz6cmr44gxg7wqvrv4aid.onion | Unknown | Large Russian DNM |

**Note:** Archetyp Market was seized by German law enforcement (per dark.fail alert, July 2026). Do not attempt.

## Hermes Cron for Automated Web Searching

For recurring research, use Hermes cron jobs (not standalone Python):

```
cronjob action=create schedule="every 12h" \
  prompt="Search these queries for [topic]..." \
  enabled_toolsets=[web, file, terminal]
```

**Never** write standalone scripts that import `from hermes_tools import web_search` — this only works inside an active Hermes agent and crashes in system crontab.

## Pitfalls

- .onion addresses change frequently (market reboots, exit scams, seizures). Always verify before relying on them.
- Interactive markets require PGP key registration, captcha, or invitation — curl can't bypass these.
- Tor is slow — set generous timeouts (15-30s connect, 30-60s max time).
- Some markets rate-limit or block non-browser user-agents. Try adding `-H "User-Agent: Mozilla/5.0"`.
- **dark.fail clearnet** shows all addresses but not their live status (status is rendered via CSS classes, not visible text). Use the .onion version for accurate uptime info.
- Markets under DDoS return 502/503 — don't immediately write them off as dead, check back next cycle.
