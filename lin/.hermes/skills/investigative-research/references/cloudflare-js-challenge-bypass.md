# Cloudflare JS Challenge — Domain Alternate Recon

## The Problem

Cloudflare JS challenges (the "I am human" / "Checking your browser" interstitial) cannot be passed by headless browsers. The challenge requires JavaScript execution with fingerprinting (mouse movement, timing, canvas, WebGL) that headless Chrome in automation mode fails.

This means any investigation target protected by Cloudflare's JS challenge is invisible via browser automation.

## The Bypass — Alternate Domains

Cloudflare protections are configured **per domain**. A site operator may protect their main domain but not their alternate TLDs. By trying every known alias domain, you often find one that serves content directly.

### Workflow

**1. Identify all known domains for the target**

The Cloudflare challenge page itself often lists the site's alias domains in its HTML SEO layer (hidden headings). Extract them:

```bash
# Fetch the CF page and grep for domain patterns
curl -skL -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" https://target-site.cm/ 2>/dev/null \
  | grep -oiE '\b[a-z0-9.-]+\.(tk|cm|mobi|la|lol|zip|cc|io|to|su|ru|xyz|top|gdn|cf|ga|ml)\b' \
  | sort -u
```

**2. Test each domain in the browser**

```bash
# List of discovered domains
for d in target.tk target.cm target.mobi target.la target.lol target.zip; do
  code=$(curl -skL -o /dev/null -w "%{http_code}" --max-time 10 "https://$d/")
  echo "$d -> HTTP $code"
done
```

**3. Navigate to the most promising ones**

HTTP 200 domains that returned body content (vs a CF wall) are candidates. Navigate the browser directly to them.

### Typical patterns

| Domain | Likely outcome | Notes |
|--------|---------------|-------|
| `.cm` (Cameroon) | Cloudflare wall | Often the main domain |
| `.la` (Laos) | **Best chance** — serves raw login page | The operator's backup that often skips the CF gate |
| `.mobi` | CF wall | Usually mirrors the main |
| `.lol` | CF wall | Usually mirrors the main |
| `.zip` | Partial — served login HTML before JS kick | Works for curl-scraping |
| `.tk` (Tokelau) | **Dead** — DNS NXDOMAIN | Free domains get seized/expire fast |
| `.cc` (Cocos) | Varies | Worth trying if listed |

### Why it works

Cloudflare configuration is TLD-specific. A site operator sets up CF on `bclub.cm` (the main) but never bothers configuring it on `bclub.la` or `bclub.zip`. The backup domain points at the same origin server but bypasses CF entirely.

The .la TLD consistently out-performs others for this pattern because Laos domains are often used as secondary/backup redirects.

### Limitations

- **Not all targets have alternate domains.** Some only operate on one TLD.
- **The operator may wrap ALL domains in CF.** If every domain serves the CF wall, the technique doesn't work.
- **Login CAPTCHAs** are separate from the CF challenge — even if you reach the login page, you may face a math captcha or reCAPTCHA that can't be automated.
- **Legal boundary** — accessing a site's login page does not equal authorization to use the service. This technique is for open-source intelligence gathering (what's publicly reachable), not for accessing private systems.
