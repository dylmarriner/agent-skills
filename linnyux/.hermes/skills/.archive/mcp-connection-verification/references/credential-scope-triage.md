# Credential-scope triage for remote provider MCPs

Provider APIs answer with numeric codes. Map the code before touching config; the overwhelming majority
of "broken MCP" reports are one missing permission group.

## Cloudflare (`mcp.cloudflare.com`)

Fuller connect/OAuth detail lives in the `native-mcp` skill's `references/cloudflare-mcp.md` (user-owned
— read, don't edit). This file carries the verification half.

Ladder:

1. `tool_search` for Cloudflare action words → `mcp__cloudflare__*` hits mean discovery ran. Cross-check
   the entry's 34-pattern `tools.exclude` (3,541 raw → 1,976 registered; drops radar, zerotrust, dlp,
   dex, gateway, devices, magic, mnm, cni, secondary_dns and similar families).
2. `get_zones` — a scoped token on the account reads the zone list even when almost nothing else works,
   so this isolates auth from permission.
3. `POST /accounts/{id}/tokens/verify` for the credential itself (account-scoped endpoint, not
   `/user/tokens/verify`).
4. The endpoint you actually need.

Error codes:

| Code / message | Meaning |
|---|---|
| `1000 Invalid API Token` | Expected from **user-level** endpoints (`/user/tokens/verify`) when the token is account-scoped. Not evidence of a bad token. |
| `9109 Valid user-level authentication not found` · `Unauthorized to access requested resource` | Token is account-scoped, so `/user`, `/memberships`, and `/accounts/{id}/tokens` all refuse. Token-management refusal uses the same code. |
| `9106 Authentication failed (status: 400)` | `/memberships` (user-level) called with an account token. |
| `10000 Authentication error` | Endpoint reachable, token lacks that permission group **for that resource** (e.g. `/zones/{z}/dns_records` without Zone:DNS). |

Observed working set for a plain account token with account/zone read + workers: `GET /zones` (with
`permissions` array — see trap), `GET /accounts`, `GET /accounts/{id}/workers/scripts`. Failing set on the
same token: `/user`, `/user/tokens/verify`, `/memberships`, `/zones/{z}/dns_records`,
`/accounts/{id}/tokens`, `/accounts/{id}/tokens/permission_groups`.

### Entitlement-array trap

`GET /zones` returns a 100+ entry `permissions` list on each zone (`#dns_records:edit`, `#worker:edit`,
`#zone_settings:edit`, `#cfone:read`, `#teams:pii`, `#magic:edit`, …). That is the **account's**
entitlements. Reporting it as the token's scopes produces a confident "DNS works" followed by a `10000
Authentication error` on the very next call. The token's own policies
(`GET /accounts/{id}/tokens/{tid}`) are the only real scope source — and that read needs
token-management permission, which a cloned token will not have.

### Rotation consequence

A token minted by cloning another while dropping the `Account API Tokens` groups can never widen its own
scope: `GET /accounts/{id}/tokens` → `9109`, `…/tokens/permission_groups` → `403`, no in-place fix.
Recovery is a dashboard re-mint (My Profile → API Tokens) with the needed grants — e.g. Zone:DNS:Read+Edit
plus Account:API Tokens:Edit if future rotations should stay self-service. When handing such a token over,
say plainly that scope cannot be extended programmatically anymore.

Install procedure for a replacement: write the value to `~/.hermes/.env` as `CLOUDFLARE_API_TOKEN=`
(referenced by `headers.Authorization: Bearer ${CLOUDFLARE_API_TOKEN}` in `config.yaml`), keep the file
`0600`, never print the value into logs or chat, then fully restart Hermes before re-verifying end to end.

## Adding another provider

Append a section with: the cheap-list probe, the account/tenant-scoped verify endpoint, a code → meaning
table for the three failure classes (user-scoped credential, missing permission group, resource-level
entitlement confusion), and the dashboard-only recovery path.
