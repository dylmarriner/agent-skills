# Etomidate Vendors Dedup — Session Reference

## Source data
- File: `/home/kubuntux/etomidate_vendors.json`
- Structure: `{vendors: [...], onion_markets: [...], last_run: "..."}`
- Before: 269 vendor entries + 5 onion markets
- After: 120 unique vendors + 5 onion markets
- Removed: 28 trash + 50 info/reference + 67 same-domain duplicates

## Categorization rules used

### Trash domains (removed entirely — search engine noise)
```
bestbuy.com, realestate.co.nz, noelleeming.co.nz, theglobe.nz,
kiwimarket.co.nz, realestate.com.au, buykiwi.co.nz, buykiwidirect.co.nz,
jiomart.com, coingecko.com, computeruniverse.net, bitpay.com, coingate.com,
kucoin.com, tabby.ai, zefame.com, flyhummingbyrd.com, yandex.com,
amazon.com, builders.co.za, salonsdirect.com, haircosmetics.co.uk,
crunchbase.com, vg247.com
```

These matched on generic "buy" / "shop" keywords in the search query. No etomidate content.

### Info/reference domains (removed — not vendors)
```
litfl.com, medicinenet.com, drugs.com, medscape.com, jove.com,
chemspider.com, cochrane.org, frontiersin.org, goodrx.com,
pharmacychecker.com, singlecare.com, icliniq.com, thennt.com,
mdedge.com, ashp.org, rxspark.com, drugpatentwatch.com, springer.com,
journals.lww.com, cognitivemarketresearch.com, koreabiomed.com,
focustaiwan.tw, thestandard.com.hk, thethaiger.com, mustsharenews.com,
metrotvnews.com, herworld.com, nams.sg, moh.gov.sg, visaverge.com,
health.govt.nz, rx.com, rxreasoner.com, lookchem.com, ecasb.com,
chemicalbook.com, chemabout.com, chemball.com, watson-int.com,
biocompare.com, enamine.net, volza.com, unitedadlabel.com,
prescriptionpoint.com, wjgnet.com, greggordon.org
```

Medical info sites, news articles, research papers, drug pricing sites, chemical directory aggregation pages.

### Same-domain merged (keep 1 per domain)

Top offenders:
- `etomidatestore.com`: 12 → 1 (root URL, multiple product pages + blog posts)
- `cannabisdispensarysshop.com`: 4 → 1
- `fishersci.com`, `lgcstandards.com`, `sigmaaldrich.com`, `clearsynth.com`: 4 each → 1
- Many other B2B suppliers had 2-3 product/category pages each

### Scoring approach
- Root URL: +10 points
- Description >50 chars: +3, >100 chars: +2
- "etomidate" in description: +3
- "buy"/"order"/"supplier" in description: +2
- "price"/"vendor"/"manufacturer": +1
- URL length penalty: -0.01 per character

## Categories in final output
- API/B2B manufacturers & suppliers: ~31
- Consumer shops (powder, K-pods, vape): ~7
- Classified/SEO spam listings: ~21
- Other (pharma distributors, medical supply): ~61
- Onion markets: 5 (Torzon, Nexus Market, Black Ops, Vortex, Drughub)
