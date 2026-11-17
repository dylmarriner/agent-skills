# NZ-Specific OSINT Sources

Direct URLs for New Zealand public-record databases that bypass search engines. Most of these are government-operated and accept direct `curl` queries. Rate-limiting is gentler than commercial search engines.

## Court & Criminal Records

| Source | URL | Type | Notes |
|---|---|---|---|
| Judicial Decisions Online | `https://www.justice.govt.nz/jdo/` | Court judgments | Supreme, Appeal, High Court. District Court coverage is spotty. Has its own search form. |
| NZLII | `https://www.nzlii.org/` | Court judgments | Richer than JDO but Cloudflare-protected. Browser tool may work; curl does not. |
| Corrections Dept | `https://www.corrections.govt.nz/` | Prison info | No public inmate search. OIA requests only. |
| Police vetting | `https://www.police.govt.nz/advice-services/businesses-and-organisations/vetting` | Criminal history | Formal vetting request (~$8.50 NZD). Not instant. |

## People & Business

| Source | URL | Type | Notes |
|---|---|---|---|
| Companies Office | `https://companies-register.companiesoffice.govt.nz/` | Director/officer search | Free. Search by name for directorships. |
| Insolvency Register | `https://www.insolvency.govt.nz/` | Bankruptcy info | Public register. |
| Electoral Roll | In-person only | Residential addresses | Not online. Available at PostShops and libraries. |
| Births Deaths Marriages | `https://www.bdmhistoricalrecords.dia.govt.nz/` | Historical records | Limited online; full records require OIA. |

## News Archives (NZ)

| Source | URL | Notes |
|---|---|---|
| NZ Herald | `https://www.nzherald.co.nz/search/` | Paywalled. Search form reachable via browser. |
| Stuff | `https://www.stuff.co.nz/search` | Less paywalled. Search form reachable via browser. |
| RNZ | `https://www.rnz.co.nz/search` | Public broadcaster, no paywall. |
| The Press | `https://www.thepress.co.nz/search` | Christchurch/South Island coverage. |
| Otago Daily Times | `https://www.odt.co.nz/search` | Dunedin/South Island coverage. |

## Social & Professional

| Source | URL | Notes |
|---|---|---|
| LinkedIn NZ | `https://nz.linkedin.com/pub/dir/First/Last/nz-0-New-Zealand` | Replace First/Last. Returns profile count. |
| Facebook NZ | `https://www.facebook.com/search/people/?q=...` | Requires login for useful results. |

## How to use these

1. Start with **Companies Office** and **JDO** — both accept direct queries and rarely rate-limit.
2. News archive searches should use site-scoped queries (e.g., `site:nzherald.co.nz "Full Name"`) on DDG HTML before hitting the site's own search.
3. For criminal history specifically, the web is near-useless for NZ individuals. The real records are in JDO (judgments only) and police vetting (full history). Set expectations accordingly.
4. **OIA requests** to Corrections, Police, or MOJ are the only way to get comprehensive criminal/custodial history for an NZ individual through legal public channels.
