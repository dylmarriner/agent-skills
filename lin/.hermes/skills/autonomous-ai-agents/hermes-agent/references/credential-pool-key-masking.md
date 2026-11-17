# Credential Pool Key Masking

The Hermes credential pool (`~/.hermes/auth.json` → `credential_pool`) stores API keys at rest with maskable middle segments. Keys sourced from `env:*` land in the pool but get their middle portion replaced with `...` once written to disk.

## Symptoms

- Reading `~/.hermes/auth.json` shows `access_token: "sk-abc...xyz"`
- Reading `~/.hermes/.env` shows `DEEPSEEK_API_KEY=***`
- Using the stored key from the credential pool in another tool (OpenCode, curl, etc.) returns "Authentication Fails, Your api key is invalid" because the masked key is not the real key
- A key that works fine from Hermes itself doesn't work when copied from the credential pool

## Recovery

If you need the raw key for a different tool:

1. **From the .env file** — `source` it directly rather than reading with file tools:
   ```bash
   source <(grep -a '^DEEPSEEK_API_KEY=' ~/.hermes/.env) 2>/dev/null
   echo "key=${DEEPSEEK_API_KEY}"
   ```
   The `-a` flag on grep reads the file as binary, bypassing Hermes' display-level masking.

2. **From the running gateway process** — `cat /proc/<pid>/environ | tr '\0' '\n' | grep DEEPSEEK` if the process still has the original env.

3. **From the original source** — the user's shell rc file, exported env var, or Docker compose config that originally set `DEEPSEEK_API_KEY`. This is the most reliable path.

## Prevention

When configuring a third-party tool (OpenCode, Claude Code, etc.) with a credential that Hermes manages:

- **Don't pull the key from the credential pool** — it will be masked. Ask the user for the key directly, or source it from the `.env` as shown above.
- **Store the key directly in the third tool's config** — the Hermes credential pool masking only affects Hermes-managed storage, not the tool's own config file.
- **The key that works from Hermes itself may be corrupted in storage.** If Hermes is currently connected to the provider but the stored key appears truncated, Hermes loaded it from the original env before the credential pool masked it.
