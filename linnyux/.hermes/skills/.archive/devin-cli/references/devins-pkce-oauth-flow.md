# Devin CLI PKCE OAuth Flow (Detailed Reference)

## Protocol

Devin uses **PKCE (Proof Key for Code Exchange)** OAuth 2.0, the standard for CLI tools that can't protect a client secret.

```
devin auth login --force-manual-token-flow
  ↓
Generates: S256(code_verifier) → code_challenge
  ↓
Builds URL: https://app.devin.ai/auth/cli/continue
  ?state=<uuid>
  &prompt=select_account
  &code_challenge=<base64-sha256>
  &code_challenge_method=S256
  ↓
User visits URL → authenticates via browser
  ↓
Devin auth server exchanges code for API key
  POST /exa.seat_management_pb.SeatManagementService/ExchangePKCEAuthorizationCode
  ↓
Response: { api_key, devin_api_url, devin_webapp_host }
  ↓
Credentials written to ~/.local/share/devin/credentials.toml
```

## Credentials File Location

```
~/.local/share/devin/credentials.toml    # API key + URLs
~/.config/devin/config.json               # CLI config (version only)
```

## Error Recovery

### "Error: Login canceled" or "Error: Failed to read code - user canceled"
→ The process didn't receive input in time. Kill it, start fresh.

### Code submitted but process hangs
→ The code was from an old session (different state/challenge). Kill the process, start fresh with a new URL.

### "Not logged in" after auth
→ Check credentials file exists. If not, re-auth. If yes, check `devin_api_url` is set correctly.

### ACP: "ACP host has not authenticated"
→ Devin in ACP mode received no API key from the host. When running standalone (not through Windsurf), this works fine because it falls back to stored credentials. When running through an ACP host that doesn't provide `windsurf-api-key`, this error appears.

## Windsurf vs Standalone Auth

| Mode | Auth method | Notes |
|------|-------------|-------|
| Bundled in Windsurf | `windsurf-api-key` passed via ACP `authenticate` | Automatic — no user action needed |
| Standalone CLI | PKCE OAuth + stored credentials | User must visit URL and paste code |
| ACP from Hermes | Falls back to stored credentials | Requires prior `devin auth login` |

## Backend Endpoints

- Auth API: `https://app.devin.ai/auth/cli/continue`
- Token exchange: `https://<api_server>/exa.seat_management_pb.SeatManagementService/ExchangePKCEAuthorizationCode`
- Windsurf API: configurable via `WINDSURF_API_SERVER_URL`, `WINDSURF_WEBSITE_URL`
- Devin API: configurable via `DEVIN_API_URL`
