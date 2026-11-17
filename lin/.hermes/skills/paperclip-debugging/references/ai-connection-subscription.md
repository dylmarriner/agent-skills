# Managed AI subscription connections (OpenAI / ChatGPT, Claude)

Use when connecting a *local subscription* AI connection fails, or when an agent's environment test rejects the connection as incompatible. Two separate 422s get confused with each other; diagnose them apart.

## 1. The sign-in flow is device-auth — Connect only works after authorization

Endpoints (company-scoped, board auth):

```sh
C=<companyId>
# start: returns sessionId only, plus expiry
curl -sS -X POST "http://127.0.0.1:3100/api/companies/$C/ai-connections/local/attempts" \
  -H 'content-type: application/json' \
  -d '{"provider":"openai","method":"subscription","name":"My OpenAI subscription","ownership":"personal","agentIds":[],"allAgents":true}'
# poll: returns {status:"sign_in_required", authorizationUrl, code}
curl -sS -X POST "http://127.0.0.1:3100/api/companies/$C/ai-connections/local/check" -H 'content-type: application/json' -d '{...same intent..., "localSessionId":"<id>"}'
# complete
curl -sS -X POST "http://127.0.0.1:3100/api/companies/$C/ai-connections/local" -H 'content-type: application/json' -d '{...same intent..., "localSessionId":"<id>"}'
```

The code must be entered at the `authorizationUrl` (e.g. `https://auth.openai.com/codex/device`) first. Completion verifies the credential file written into the attempt home (`~/.paperclip/instances/default/ai-local-logins/<sessionId>/`) and, for OpenAI, also calls the quota API. Pressing Connect before that lands returns:

> `Could not verify the local subscription. Finish browser sign-in for this connection, then try Connect again.`

That 422 is timing, not a broken provider — the next attempt after the user finishes the device page returns 201. Attempts expire in 30 min; cancel with `DELETE .../local/attempts/<id>` rather than leaving them open.

Handler is `server/src/services/local-ai-login.ts` (`start`/`check`/`complete`/`cancel`); verifier is `server/src/services/local-ai-credentials.ts` (OpenAI reads `auth.json` from the login home, then calls the quota API).

## 2. `ai_connection_incompatible` — the real blocker

`assertManagedAiProjectAuth` in `server/src/services/ai-connection-runtime.ts` walks up from the agent cwd and greps each `.codex/config.toml` (openai) / `.claude/settings*.json` (anthropic) for:

```
apiKeyHelper|ANTHROPIC_API_KEY|ANTHROPIC_AUTH_TOKEN|CLAUDE_CODE_OAUTH_TOKEN|OPENAI_API_KEY|model_provider[[:space:]]*=|env_key[[:space:]]*=|experimental_bearer_token|cli_auth_credentials_store
```

Any hit → 422: `This agent's managed AI connection conflicts with project authentication settings in .codex/config.toml`. The walk reaches the *user's global* `~/.codex/config.toml`, because it appends `.codex/config.toml` to every ancestor directory — a global config with its own `model_provider`/`env_key` routing blocks every agent under `$HOME`.

Reproduce the exact failure against the agent's environment before touching config:

```sh
curl -sS -X POST "http://127.0.0.1:3100/api/companies/$C/adapters/codex_local/test-environment" \
  -H 'content-type: application/json' \
  -d '{"runner":"legacy","aiConnection":{"provider":"openai","method":"subscription","mode":"responsible_user"},"agentId":"<agentId>","adapterConfig":{},"environmentId":"<envId>"}'
```

A pass returns `status: pass` with `codex_native_auth_present` and a hello probe; the agent is then usable.

### Pitfall: commenting out the keys does not clear the check
The check is a flat text grep, so `# model_provider = "x"` still matches AND still contains `OPENAI_API_KEY`/`env_key`. **Delete** the conflicting lines. Back the file up first (`cp -a ~/.codex/config.toml ~/.codex/config.toml.bak-<tag>`) and re-validate with `python3 -c "import tomllib;tomllib.load(open('<path>','rb'))"`.

Removing them is a real behaviour change on the host: dropping `model_provider` makes plain `codex` fall back to the default provider (still honouring `openai_base_url` if set, so a local proxy stays in path and must be running), and dropping `env_key` breaks manual `--provider` selection that relied on the env var. State both, and offer the alternative — keep the routing and use an API-key connection for that agent instead of a subscription.

Confirm isolation instead of assuming it: an ACP-engine agent gets its own `CODEX_HOME`, so the global config only matters through this ancestor grep, not at run time.

## Useful read-only state

```sh
curl -sS "http://127.0.0.1:3100/api/companies/$C/ai-connections"   # connections, status, accountLabel, isDefault
curl -sS "http://127.0.0.1:3100/api/companies/$C/agents"           # agent adapterConfig / lifecycleHolds
# the server log carries the 422 request bodies (dev log or the instance server.log)
```
