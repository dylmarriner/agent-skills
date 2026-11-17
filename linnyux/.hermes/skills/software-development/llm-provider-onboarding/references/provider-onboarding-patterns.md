# Provider onboarding patterns

This reference condenses the session learning into reusable notes.

## DeepSeek API

- Treat DeepSeek as a standard cloud API provider with its own key.
- Use the OpenAI-compatible base URL: `https://api.deepseek.com/v1`.
- Typical model ids:
  - `deepseek-chat`
  - `deepseek-reasoner`
- Route workloads with an explicit provider slug plus model id, rather than trying to reuse another vendor's slug.

## OpenAI-compatible endpoints

- Many apps only need:
  - a base URL that ends in `/v1`
  - an API key or bearer token
  - a working `/models` endpoint
- Verify the endpoint shape before wiring the UI; a valid auth token is not enough if model discovery fails.

## CLI-auth reuse / subscription login

- Some providers are better handled as subscription/OAuth flows than as raw keys.
- A common pattern is importing an existing CLI auth file instead of asking the user to re-authenticate.
- Example from the session: OpenHuman can import Codex CLI auth from `~/.codex/auth.json` and store it as an OpenAI OAuth profile.

## Practical advice

- Ask: does the app want an API key, an OAuth profile, or a local process?
- Check whether the app can import auth from another product's CLI before inventing a manual workaround.
- Keep the provider routing grammar and the auth source separate in your mental model.

## Provider base_url resolution order (Hermes-specific)

When configuring an LLM provider in Hermes, the API endpoint URL resolves in this hierarchy (highest priority first):

1. **`config.yaml` → `model.base_url`** — the `base_url` key under the top-level `model:` section. This **overrides** everything below. A stale entry from a previous provider persists after switching providers.
2. **Built-in provider profile** — the provider plugin (e.g. `plugins/model-providers/deepseek/__init__.py`) defines a default `base_url` like `https://api.deepseek.com/v1`.
3. **Environment variables** (e.g. `DEEPSEEK_BASE_URL` in `.env`) — only used when neither of the above is set.

**Pitfall:** Switching from OpenAI Codex to DeepSeek leaves the old `model.base_url` pointing at `https://chatgpt.com/backend-api/codex`. This overrides the DeepSeek provider profile's correct default `https://api.deepseek.com/v1`. The `DEEPSEEK_BASE_URL` env var in `.env` may have the right value but gets ignored because the config.yaml entry takes precedence.

**Fix:** Either set the correct URL or clear it so the provider profile default is used:
```bash
hermes config set model.base_url https://api.deepseek.com/v1
# OR
hermes config set model.base_url ""
```

Note: the `DEEPSEEK_API_KEY` from `.env` IS still loaded for auth — the env var override only affects the URL, not the key.
