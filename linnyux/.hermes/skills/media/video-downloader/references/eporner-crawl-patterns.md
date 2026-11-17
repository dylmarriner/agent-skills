---
name: eporner-crawl-patterns
description: Eporner.com search patterns, tag page structures, and filtering rules for performer POV crawls
---

# Eporner.com Crawl Patterns

## Performer search template

For each performer, scrape from these sources in priority order:

### Source 1: Tag page (best for POV-specific)
```
https://www.eporner.com/tag/<performer-name>-pov/
```
Extract:
```bash
curl -sL "https://www.eporner.com/tag/<name>-pov/" \
  | grep -oP 'href="/hd-porn/[^"]*"|href="/video-[^"]*"'
```

Note: If performer name has spaces, replace with hyphens.
Examples: `lana-rhoades-pov`, `mia-malkova-pov`, `blake-blossom-pov`

### Source 2: Pornstar page
```
https://www.eporner.com/pornstar/<name>/
```
Pornstar page has ALL their videos, not just POV. Filter with grep for "pov" in title.

### Source 3: Search page
```
https://www.eporner.com/search/?q=<name>+pov+hd
```

### Source 4: Category pages (for generic POV searches)
Top big tits POV:
```
https://www.eporner.com/categories/big-tits/?sort=rating&page=1
https://www.eporner.com/categories/big-tits/?sort=rating&page=2
```

Most watched big tits:
```
https://www.eporner.com/categories/big-tits/?sort=views&page=1
```

## Filtering rules

### Exclude BBC/interracial
When user says "no BBC", filter with:
```bash
# Check each URL's title before downloading
curl -sL "$URL" | grep -iP '<title>.*</title>' \
  | grep -ivE 'bbc|big.black|interracial|big.black.cock|black.cock|bwc'
```

Keywords to filter (case-insensitive): bbc, interracial, bwc, ebony, black cock, big black

### Exclude previews (short clips)
Skip any video under 2 minutes:
```bash
yt-dlp --skip-download --print duration "$URL"
```

## Performers identified for POV crawl

This user's known performer POV crawl targets:
- Lana Rhoades
- Lauren Phillips
- Angela White
- Alanna Pow
- Kendra Sunderland
- Blake Blossom
- Blondie Fesser
- Karma RX
- Violet Myers
- Mia Malkova
- Mia Melano
- Nicole Doshi
- Sharon Lee (Asian)
- Lena Paul
- Payton Preslee
- Sophie Dee
- Lexi (Luna? Lorena? — check both)
- Sky Bri
- Kali Roses
- Ava Nicks
- Natasha Nice
- Vivian Taylor
- Alexis (multiple Alexis — check Alexis Fawx, Alexis Texas)
- Emily (Emily Norman)
- Rissa (Rissa Indulges)
- Aleksa Mink
- Faith
- Camila Castillo
- Bubblebratz
- Riley (Riley Reid)
- TruKait
- Atlanta Moreno
- Dan Dangler

## Naming conventions

Use 2-letter category prefixes for all crawl downloads:
```
lr_   Lana Rhoades
lp_   Lauren Phillips
aw_   Angela White
ap_   Alanna Pow
ks_   Kendra Sunderland
bb_   Blake Blossom
bf_   Blondie Fesser
kr_   Karma RX
vm_   Violet Myers
mm_   Mia Malkova
ml_   Mia Melano
nd_   Nicole Doshi
sl_   Sharon Lee
len_  Lena Paul
pp_   Payton Preslee
sd_   Sophie Dee
lx_   Lexi
sb_   Sky Bri
kal_  Kali Roses
an_   Ava Nicks
nn_   Natasha Nice
vt_   Vivian Taylor
al_   Alexis
em_   Emily Norman
ri_   Rissa
amk_  Aleksa Mink
fa_   Faith
cc_   Camila Castillo
bub_  Bubblebratz
r_r_  Riley Reid
tk_   TruKait
am_   Atlanta Moreno
dd_   Dan Dangler
bt_   Big Tits POV (general)
```

## Rate limiting

- Max 3 concurrent yt-dlp processes to eporner
- Rate limit: `--limit-rate 5M` or use url2video service which manages concurrency
- If getting 403 errors, add `--referer "https://www.eporner.com/"` and `--add-header "Origin:https://www.eporner.com"`
- Wait 2-3 seconds between queueing sequential downloads
