# NZ Sources — beyond the government registers

The court, corrections, OIA, news-archive and gang-intelligence patterns live in the
`osint-references` SKILL.md body under "NZ-Specific Search Patterns" and "Gang
Investigation Methodology" — read those first. This file covers everything else, plus
the levers that make a NZ subject actually removable.

## Residential directory — check it early; absence is a finding

`personlookup.co.nz` advertises records on 4M+ New Zealanders: **name → landline → full
street address → neighbours**, plus reverse lookup (number → name). Google-indexed, and
much is visible without paying. It also carries per-company employee directories at
`/c/<company-slug>/<n>`.

Two things to do with it:

1. Search the subject. **Absence is a key positive finding** — it is the main reason a NZ
   resident's address is not publicly searchable, and it belongs in the "checked and not
   found" table rather than being left unmentioned.
2. If present, the subject can request suppression; escalate to the Office of the Privacy
   Commissioner on refusal.

Do **not** harvest relatives' addresses out of it — see the family-link rule in
`people-company-footprint-audit.md`.

## Other open sources worth sweeping

| Source | Where | Yields |
|---|---|---|
| NZ Gazette | `gazette.govt.nz` | official notices, appointments, marriage celebrants |
| Charities Register | `register.charities.govt.nz` | officers of registered charities |
| Incorporated Societies | `societies.govt.nz` | society officers |
| NZBN | `nzbn.govt.nz` | entity lookup |
| PPSR | via Companies Office | security interests over goods |
| Property listings | `oneroof.co.nz`, `homes.co.nz` | sold history — but address-keyed, so it rarely surfaces from a name search |

## Restricted — needs a lawful purpose, or the subject's own hand

- **Credit and identity** — Centrix, Equifax NZ, illion. The *subject* can pull their own
  free credit report; third-party access needs a statutory ground. Hand them the step.
- **Motor vehicle register** — registered-person lookup is restricted under the Privacy Act.
- **LINZ** — land titles by owner; not open-indexed, needs a formal request.
- **Electoral roll** — not published or indexed; accessible only to approved organisations.

## Breach context

`haveibeenpwned.com` is the legitimate check and needs the subject's own email address.
Notable mass-impact NZ breaches: **ManageMyHealth** (health records) and **Neighbourly**
(usernames, emails, GPS coordinates, posts, messages).

## Which commercial brokers actually hold NZ residents

| Holds NZ professional data | US-only — expect near-total noise on a NZ name |
|---|---|
| RocketReach, ZoomInfo, AeroLeads, Lusha, Apollo, Hunter.io, ContactOut, SignalHire, Cognism, Clearbit | BeenVerified, TruthFinder, Spokeo, Intelius, Radaris, PeopleFinders, Whitepages Premium, MyLife, Instant Checkmate |

The US column manufactures enormous false-positive volume on a NZ name. Report it as
noise rather than as subject records, and tell the subject not to try to disambiguate
themselves from it.

## The lever that makes NZ subjects actually removable

**Privacy Act 2020** — IPP 6 (access), IPP 7 (correction), and free complaints to the
Office of the Privacy Commissioner. Binding on NZ organisations, so volunteer clubs and
local directories comply readily. Offshore brokers ignore it: cite **GDPR/CCPA alongside
it in the same letter**, because the European-style erasure request is cheaper for them to
honour than to litigate.

**For "what do these companies hold on me", a subject access request beats a paid search.**
Under the Privacy Act, GDPR or CCPA the subject can demand the company's *entire* file on
them — free, enforceable, and it returns more than a paid lookup shows: what is held, where
it came from, who it was shared with. Route them there rather than selling them a partial
view.

## Naming pitfalls

- **Hyphenated composite surnames frequently denote a single whānau.** An uncommon
  hyphenated surname is a family-level fingerprint — it ties a whole family's public records
  together, so one member's filing can make another's suburb derivable. Report the
  *mechanism*; do not walk the family tree.
- **Search the exact spelling and hyphenation before concluding anything.** Misspelling
  returns unrelated hits off the component surnames and produces false "not found"
  conclusions. Ask for maiden, married and former surnames early — each is a separate search.
- **Macrons matter** — search both macron and non-macron forms for Māori place and
  organisation names.
