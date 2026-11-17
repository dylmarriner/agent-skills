# Synapse LLM Proxy — Transparent Memory Middleware

A lightweight HTTP server that sits between the agent and the LLM, providing
automatic context injection and memory capture without any tool calls.

## Architecture

```
                     ┌──────────────────────────────────────────┐
                     │          Synapse LLM Proxy               │
                     │  (:8768)                                 │
Agent ──POST /v1/chat/completions──►                             │
                     │    │                                      │
                     │    ├─ 1. Extract user message             │
                     │    ├─ 2. syn_context(query) ──► Synapse   │
                     │    │      └─ returns relevant memories    │
                     │    ├─ 3. Inject context into system msg   │
                     │    ├─ 4. Forward to real LLM (DeepSeek)   │
                     │    ├─ 5. Receive response                 │
                     │    ├─ 6. extract_facts() auto-store facts │
                     │    └─ 7. Return response to agent         │
                     │                                          │
                     └──────────────────────────────────────────┘
```

## Implementation

Single Python file (`proxy.py`) using only stdlib (`http.server`, `urllib`).
No dependencies beyond what's in the project venv.

### Key components:

**MCP Client (`_syn_call`)** — reuses the same MCP session management as the
Synapse server, talks to the Synapse MCP server to call `context` and `store`.

**Context injection** — on each request, extracts the user's message, calls
`syn_context()` which hits Synapse's `context` tool, and prepends the results
to the system prompt as:

```
[Synapse Memory — automatically loaded context]
[semantic 90%] Auth uses JWT RS256 signing...
[episodic 80%] Fixed LetsEncrypt cert expiry...
```

**Fact extraction** — after the LLM responds, scans the Q&A text for patterns:

| Pattern | Kind | Importance | Example |
|---------|------|------------|---------|
| Architecture decisions | semantic | 0.8 | "We use Redis for caching" |
| Commands/fixes | episodic | 0.7 | "Run `npm run migrate` to update" |
| Errors/gotchas | semantic | 0.85 | "Got stuck because port 3000 was in use" |
| URL references | episodic | 0.5 | "See https://docs.example.com" |
| Env var configs | semantic | 0.6 | "Set NODE_ENV=production" |

## Configuration

```bash
# Start pointing to DeepSeek:
LLM_PROVIDER_URL=https://api.deepseek.com/v1 \
LLM_MODEL=deepseek-chat \
LLM_API_KEY=$DEEPSEEK_API_KEY \
SYNAPSE_URL=http://100.68.0.96:8765/mcp \
python3 proxy.py

# Start pointing to Groq:
LLM_PROVIDER_URL=https://api.groq.com/openai/v1 \
LLM_MODEL=llama-3.3-70b-versatile \
LLM_API_KEY=$GROQ_API_KEY \
SYNAPSE_URL=http://100.68.0.96:8765/mcp \
python3 proxy.py
```

## Deployment (multi-machine)

**Critical: run the proxy alongside the MCP server on the same machine.**
Do NOT run it on a different machine — if the proxy host goes down, all
agents lose LLM access. Running both on the same central server means a
single restart brings everything back.

```bash
# On the central server (e.g. rabuntu):
LLM_PROVIDER_URL=https://api.deepseek.com/v1 LLM_MODEL=deepseek-chat \
  LLM_API_KEY=$DEEPSEEK_API_KEY \
  SYNAPSE_URL=http://100.68.0.96:8765/mcp \
  nohup python3 proxy.py > /tmp/proxy.log 2>&1 &
```

All agents (Hermes, OpenClaw, etc.) on all machines point their
`model.base_url` to the proxy's Tailscale IP, same machine as the MCP server:

```yaml
# Hermes config.yaml on every machine:
model:
  base_url: http://100.68.0.96:8768/v1   # ← proxy, same IP as MCP
  api_key: sk-proxy
```

This way every LLM call from any machine automatically gets context injection
and fact storage — no manual tool calls, no per-machine setup beyond changing
the `base_url` in the agent's config.

## Pitfalls

- The proxy must be running **before** the agent starts (nohup or systemd)
- Each request adds ~200-500ms for the Synapse context query
- The first request is slow (~1s) due to MCP session initialization
- Regex-based fact extraction is imperfect — it captures patterns but misses
  nuanced information. Can be augmented with an LLM-based extractor in the future.
- The proxy doesn't support streaming (SSE) in the current implementation
- All agents sharing one proxy means a single point of failure — restart the
  proxy if it crashes
- **Model name mismatch**: The proxy's `LLM_MODEL` env var must match a model
  the upstream provider actually serves. Hermes' `model.default` (e.g.
  `deepseek-v4-flash`) is the Hermes-side label and often differs from the
  provider's model ID (e.g. `deepseek-chat`). If you get 400 errors, check
  which model IDs the upstream provider exposes via its `/v1/models` endpoint
  and match `LLM_MODEL` to one of those, not Hermes' internal name.
