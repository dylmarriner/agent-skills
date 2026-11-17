# ChimeraTool Reseller API (vendor API access, not binary RE)

Fastest path to programmatic ChimeraTool access. This is the vendor's **public reseller API** — no reversing required, and it does not touch the client's licence server.

## What it is / is not

Billing + back-office only: credit balances and transfers, licence sales/extensions/upgrades, user and ChimeraCard lookups. **There is no device-procedure endpoint** — FRP removal, IMEI repair, patch cert, firmware flashing all run only in the Windows client against the Authenticator/licence, locally over USB. "Access Chimera via API" buys the ability to sell credits, not to unlock phones.

## Endpoint

    https://chimeratool.com/rapi/<cmd>        GET, urlencoded query, JSON response
    ?username=<reseller>&apikey=<key>         no signature, key from the reseller dashboard

The reseller dashboard lives at `https://chimeratool.com/reseller/`. First call can return `104` until an unread important reseller message there is read and accepted.

A browser `User-Agent` header is required — Cloudflare 403s urllib's default UA, which surfaces as a generic connection failure.

## Command table

Verified live by unauthenticated route probing (JSON auth error = exists, 404 = does not). 12 commands:

    info  list  transfer  revoke  checkuser  checkuserlicences
    checkchimeracard  selllicence  extendlicence  upgradelicence
    availableLicences  revokelicence

Parameters (from the official PHP class and the help doc):

| Command | Required | Optional |
|---------|----------|----------|
| `info` | — | — |
| `list` | — | `page`, `limit` (max 200) |
| `transfer` | `userId`, `amount` | — |
| `revoke` | `transferId` | — |
| `checkuser` | `user` | `email` |
| `checkuserlicences` | `user` | `email` |
| `checkchimeracard` | `serialnumber` | — |
| `selllicence` | `targetid`, `targettype` (`user`/`chimeracard`), `licencename` | — |
| `extendlicence` | `userlicenceid` | — |
| `upgradelicence` | `userlicenceid` | `licencename` (`Pro`/`Premium`) |
| `availableLicences` | — | — |
| `revokelicence` | `actionId` | — |

## Upstream drift (found by probing, not documented anywhere)

- `listsoldlicences` ships in the official PHP class (`https://pics.chimeratool.com/chimeratoolapi.tar.gz`) but **404s on the live server**. The sold-licence listing is gone or renamed; it was also the documented way to obtain `actionId`s for `revokelicence`.
- `buyLicencePrices()` is described in the help doc but appears in no shipped client, and no command string was findable across ~10 candidate spellings. Treat as unavailable rather than guessing.

Re-probe the table before trusting it — run the client's `routes` subcommand.

## Error code map (highlights)

    100 no username/apikey given     101 bad username/apikey
    102 user inactive                103 user locked/banned
    104 unread important reseller message (read it at /reseller/)
    105 not eligible for reseller status
    404 not enough credits (transfer)   405 can't find userId
    408 minimum transferable amount is 20000 credits
    409 maximum transferable amount is 18000 credits
    807 not enough credit (sell licence)
    901/1001 userlicenceid missing; 902/1002 licence not found
    1102 licence revoke window is 1 day

Note 408 vs 409 as shipped: the min/max pair is contradictory in the vendor's own doc. Trust the live response, not the table.

## Reseller entry conditions

- Minimum purchase **20,000 credits** from one of two distributors (GsmEasy, GsmServer) — no other route, circle won't expand. ~$2,000 USD list, 8% reseller discount. Non-refundable. Must rebuy 20,000+ at least once every 4 months or status is withdrawn.
- Manual approval, valid 4 months at a time.
- Requires a public website showing Chimera prices without login, operator contact info, and accepted payment methods.
- Mandatory end-user auth flow before checkout: MD5 of the reseller username as `chimeraConfig.hash` on the username input field, plus the `chimeraAuthSuccess` JS event gating the checkout button. Cannot be disabled.
- Exclusion triggers include a PayPal/payment claim on the account and undercutting the end-user price.
- For scale: single end-user licences start at $99.90 and partner entry is ~18x that and recurring — only worth it when actually reselling. See the retail table below.

## Customer route: buy from a reseller, hold no key

The entry conditions above bind the *reseller*, never the customer. A retail customer needs no apikey and no minimum: pick any reseller from the vendor's published list (`/<lang>/resellers`), pay them, hand them your Chimera username, and **their** key does the provisioning call on your behalf:

    selllicence?username=<reseller>&apikey=<reseller>&targetid=<YOUR_USER_ID>&targettype=user&licencename=Basic
    transfer?userId=<YOUR_USER_ID>&amount=<credits>

So "get access through someone else's API key" is the normal retail flow, not a workaround — the reseller is the payment-and-provisioning agent and the 20k float is their problem. Licence and credits land on the account within minutes (1-10 min typical). Getting a `userId` for them to target: the reseller can `checkuser` it, or the client shows the account name.

## Retail prices (scraped from a live reseller panel)

| Item | Standard tier | Bulk / normal tier |
|------|---------------|--------------------|
| Licence Basic (100 devices / 1 yr) | $104.90 | $99.90 |
| Licence Professional (1500 devices / 1 yr) | $154.90 | $149.50 |
| Licence Premium (5000 devices / 1 yr) | $194.90 | $189.50 |
| Credits | $0.110/cr | $0.100/cr (lowest seen $0.097) |

Payment channels resellers carry that the vendor shop may not: USDT/crypto, PayPal, card, SEPA EUR + USD wire, Wise, Payoneer.

**Buy at list.** Undercutting the end-user price is a vendor exclusion trigger, so a reseller quoting below $99.90 Basic or below $0.10/credit is out of compliance and the licence on your account can be revoked along with theirs.

### Scraping a reseller price list

Most resellers run a DHRU Fusion panel. Tells: `?selectlanguage=<Lang>&lcode=XX` links, a `resellerpricing/...` nav, and a `/pages/faq` + `/pages/terms` + `/register` pairing. There is no product search worth using — `/search?q=...` 404s.

- Plain curl returns an empty JS shell; these are client-rendered. Drive a real browser.
- Price tables live under `/resellerpricing/<service>`; the tool/credit table is **`/resellerpricing/server`** (`/resellerpricing/file` and the IMEI page carry nothing useful).
- The raw table-cell text already contains every tier's price — query the DOM for rows mentioning the product and keep text nodes under ~180 chars, no cell parsing needed:

      js("""(() => {const o=[];document.querySelectorAll('tr,.product,li,div').forEach(el=>{
        const t=(el.innerText||'').trim().replace(/\\s+/g,' ');
        if(/chimera/i.test(t)&&t.length<180)o.push(t);});
        return JSON.stringify([...new Set(o)].slice(0,25));})()""")

## Account signup

`/<lang>/signup` = username, email, email again, language, a text captcha (an image — readable with vision), and a terms checkbox. The GTC restricts the software to business use (legal entities, sole traders, professional organisations) and forbids sharing a licence. A verification email follows; where the Gmail API is unavailable to the agent, the user clicks the link themselves.

## Client

`/home/lin/chimeratool-api/chimera_rapi.py` — stdlib-only (urllib), config from `--user/--apikey` > `$CHIMERA_RESELLER_USER`/`$CHIMERA_RESELLER_APIKEY` > `~/.config/chimeratool/rapi.json`.

    python3 chimera_rapi.py selftest        # asserts 100 on bare URL, 101 on bad creds, every table route live
    python3 chimera_rapi.py routes          # re-probe the live command table
    python3 chimera_rapi.py info            # then any command with key=value params

The `selftest` route loop is the regression check — it fails loudly the moment a command is removed or renamed upstream.
