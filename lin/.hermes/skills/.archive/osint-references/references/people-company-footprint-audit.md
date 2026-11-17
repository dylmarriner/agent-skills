# People & Company Footprint Audit — Source Map, Remediation, Deliverable

Use for: a consent-gated self-audit of a private individual, or the person-workflow pass on a named target where the answer is "what is publicly findable about this person". Covers the non-government sources that actually carry personal and company records, what to tell the subject to do about the exposure, and how to render the report for a non-technical reader.

Companion to `nz-osint-sources.md` (which covers government databases, courts, OIA paths). This file covers everything that is *not* a government register.

---

## Source map, ranked by what each actually yields

### 1. Company-register mirrors — highest yield for family-level linkage

The official Companies Register is an awkward SPA. These private mirrors are plain HTML, fully indexed, and carry director and shareholder names *with suburban addresses and appointment dates*:

- `bizdb.co.nz/company/<company-number>/` — directors, shareholders, full address history, appointment/termination dates, prior name changes
- `businesscheck.co.nz/ltd/<NZBN>/` — same, plus previous addresses and share allocations per shareholder group
- `companiesnz.com`, `newzealand-company.com` — director lists, often with partially published residential addresses
- `personlookup.co.nz` — primarily a **residential directory** (name → landline → full street address → neighbours, plus reverse number lookup, 4M+ records, Google-indexed); also carries per-company employee directories at `/c/<company-slug>/<n>`. Search the subject here early — **absence from it is a positive finding worth reporting**, since it is the main reason a NZ resident's address is not publicly searchable. See `nz-osint-sources.md`.

**Why this matters more than it looks.** A person with an uncommon hyphenated or multi-part surname is a *family fingerprint*. Even when the subject has no directorships of their own, the surname pulls up relatives' companies with residential suburbs attached, which narrows where the subject lives. Confirm the subject is clean, then report the *mechanism* only — the surname is what makes their suburb derivable. Do **not** build a roster of relatives' addresses, numbers or filings: they have not consented to anything, and their details are not a finding about the subject.

### 2. B2B lead-generation brokers — highest practical abuse risk

- `rocketreach.co` — advertises "<name> Email & Phone Number"; the page states *how many* emails it holds for the person
- `zoominfo.com/p/<Name>/<id>` — title, tenure, employer summary, work location
- `aeroleads.com` — lists a person as a "colleague" on every co-worker's profile page

Two behaviours to expect: they list your target as a named colleague on **other people's** profiles (so a name search surfaces them buried inside a third party's page), and their actual product is gated contact data. The exposure is the *availability*, not the page content.

**Escalation rule:** if the subject's role is adjacent to money movement, approvals, or privileged access, this is a spear-phishing profile and is graded HIGH, not MODERATE. Report the mechanism explicitly — an attacker with name + employer + exact department function + a purchasable route to the work inbox can build a convincing fake supplier or internal request.

### 3. Volunteer organisation and school documents — most common serious finding

Sports clubs, school boards, alumni registers and community groups publish names and contact details routinely, usually as PDFs or plain HTML, and search engines index them:

- **Club award/honours PDFs** — list members with their roles, and frequently the age-group teams their children played in
- **Club contact pages** — routinely publish committee members' **mobile numbers** in plain text
- **School alumni registers** — name plus year

Search pattern: `<surname>` combined with club/school terms, and the surname alone against document-hosting patterns (PDFs index well).

These are the only findings that routinely create a genuine *physical-safety* risk, because a named minor plus parent plus club converts into a weekly, predictable location once the club's public fixtures and grounds are checked. Rank them first in any report and name them as the priority action.

### 4. Facebook reaction and comment indexing — highest volume

Reactions and comments on **public pages and groups** are individually visible and search-indexed with the full name attached. The subject almost never knows this. Volume comes from brand pages, restaurants, community groups, and — critically — posts where they are **tagged by someone else**.

What assembles from this: suburb inference (local gym, local clubs, local restaurants), family relationships (tagged relatives), group memberships, travel history, stated interests.

Search pattern: run `"<full name>" -site:linkedin.com -site:facebook.com` first to isolate non-social sources, then `"<full name>" facebook <suburb or apparent interest>` to surface the social layer.

Also worth checking: the subject's `likes` on LinkedIn. LinkedIn surfaces reaction listings publicly and search engines index them with the name attached, so third-party posts (health topics, politics, workplace commentary) become searchable statements *about* the subject without the subject having posted anything.

### 5. Content that yields nothing — check it anyway

Deliberately check and report as positives: home address under the name, personal phone number, non-Facebook social platforms, news coverage, court judgments, insolvency, fines, and director/shareholder roles. A short **"checked and not found"** table is as valuable to the subject as the findings — it is the half that stops them panicking.

---

## Identity anchors to expect

A single public LinkedIn profile typically supplies: employer, exact title, start dates, a full role-by-role timeline *with dates*, a verbatim job description, award history, and often secondary school (via a broker record cross-reference).

Report the **dates** specifically. A dated employment history is the raw material for institutional identity-verification questions, and many organisations still use previous-employer or dates-of-employment as a security check.

---

## Remediation ladder — what to tell the subject

Ordered by exposure removed per minute spent.

1. **Volunteer-organisation documents first.** Email the club/school, ask them to redact and re-upload, then submit the changed URL to Google for re-indexing. Highest consequence, lowest effort, and domestic organisations comply immediately. Supply the subject with copy-paste-ready wording — they should not have to compose the ask.
2. **Facebook search-engine indexing.** Settings → Privacy → *"Do you want search engines outside of Facebook to link to your profile?"* → **No**. One toggle kills the largest volume block. Existing cached results fade over weeks rather than instantly — say so, or they will re-check in a day and think it failed.
3. **Facebook past activity.** Settings → Activity Log → Manage Activity, restrict audience on past posts and comments.
4. **LinkedIn.** Settings & Privacy → Visibility → Public profile → turn off public visibility; remove secondary school; reduce activity broadcasts. Note honestly that LinkedIn limits how much reaction visibility can be hidden.
5. **Data brokers.** Email `privacy@rocketreach.co`, `privacy@zoominfo.com`, `support@aeroleads.com`. Cite the NZ Privacy Act 2020 **plus GDPR/CCPA** — offshore companies respond to the GDPR framing because it is cheaper than the legal risk, and the Privacy Act alone is hard to enforce extraterritorially. Expect to send the RocketReach request twice.
6. **Google "Results about you"** for anything showing contact details, plus page-refresh requests once the source pages change.
7. **haveibeenpwned.com** for breach exposure. This requires the subject's own email address, so it is a step you hand to them rather than run.
8. **Workplace security team** when the subject's role is adjacent to money movement, approvals, or privileged access. Banks and similar employers want to know their operational staff appear in lead-gen databases.

---

## Deliverable format for a non-technical subject

The main skill's output contract (markdown dossier plus `findings.json`) is right for an analyst working the case. When the report is going to the **subject** — a non-technical person reading about themselves — produce a self-contained HTML file and render a PDF, because it forwards and prints cleanly.

```bash
google-chrome --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
  --print-to-pdf=/abs/out.pdf file:///abs/in.html
```

Then verify the **rendered artifact**, not the source file:

```bash
pdfinfo out.pdf | grep -Ei 'pages|size'          # did it produce pages; letter vs A4
pdftotext -f 1 -l 1 out.pdf - | grep -i '<edited string>'   # did a late edit actually land
pdftoppm -png -r 70 -f N -l N out.pdf /tmp/p     # render a page and LOOK at it
```

The image check is not optional — table overlap and broken styling do not show up in text extraction, and a stale cross-reference (pointing at the wrong section) only surfaces when you read the rendered page. Verify the specific string you changed arrived in the output.

CSS constraints: self-contained only (no external fonts, no CDNs) so the file works offline; include `@media print` rules and `page-break-inside: avoid` on finding blocks so sections do not split across pages.

Structure that works:

1. Cover meta block with overall severity rating and the **priority action named**
2. "What this report is" framing paragraph (sources are public; nothing private was accessed)
3. Contents
4. Executive summary as a severity table
5. Findings by category, each with its source URL and a *why this matters* paragraph
6. "What was NOT found" table
7. False-positive table (name collisions that are not the subject)
8. The real risks, with the attack mechanism spelled out
9. Ordered action plan with ready-to-send wording
10. Legal rights section
11. Appendix of every source URL
12. Appendix of scope gaps — what was not checked, and why

Every finding carries a *why it matters* paragraph. The subject cannot act on "your name is on a PDF" without knowing the mechanism that makes it a problem.

---

## Pitfalls

- **A minor's name outranks every other finding.** Name it as the priority action on the cover, with the mechanism in one line (name + parent + fixed weekly location + published fixtures). Do not bury it in a findings list where it competes with Facebook noise.
- **Do not dump non-public material.** Breach records and leaked datasets are not "public sources". Report that the exposure exists and where; never reproduce the contents. Same for a phone number a broker merely *claims* to hold — cite the claim, do not go and buy it.
- **Name collisions are protective — advise the subject NOT to fix them.** Unrelated same-name records (overseas profiles, a namesake in the news) make the subject harder to isolate. Explicitly tell them not to try to disambiguate themselves from these.
- **A null result under one surname is not a small footprint.** Maiden, married and former surnames are separate searches. Ask for them before concluding anything.
- **Search engines index continuously and caches outlive edits.** Date the assessment, and tell the subject to re-check four to six weeks after remediation rather than immediately.
- **Report an absence as an absence of *open-index* presence only.** "Not found" means not on the publicly indexed web — not that it does not exist. Electoral roll, paid people-search databases and LINZ property records require a formal request or payment; list them as explicit gaps rather than implying they were checked.
- **Verify an exposure is still live before asserting it is.** `curl -sS -o /dev/null -w '%{http_code}' <url>` — a 200 means the document is still published and the removal action is still outstanding. Do this at report time so the priority action is stated as current rather than assumed, and re-check after the subject acts rather than trusting that they did.
- **Patching the report breaks its own cross-references.** Inserting or renumbering a section moves content while "see Section N" strings stay behind — a stale pointer only surfaces when you read the rendered page. After any structural edit run `pdftotext out.pdf - | grep -o "Section [0-9]*"` and confirm each target exists. Related: when the contents list anchors to element ids, add **suffixed** sections (`10.1`) instead of renumbering, or every `href="#sN"` silently breaks.
- **Identical output size does not mean a stale render.** Replacing a section reference changes one character, so the PDF byte count can be identical while the content is updated. Verify by extracting text and grepping for the edited string, never by comparing file size.
