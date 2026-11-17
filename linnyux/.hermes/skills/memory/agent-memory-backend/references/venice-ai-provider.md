# Venice.ai as agentmemory Provider

Venice.ai serves DeepSeek models via an OpenAI-compatible API. Use it
when you don't have a raw DeepSeek API key but DO have a Venice API key
(common pattern — Venice is free and uncensored).

## Config in ~/.agentmemory/.env

```ini
OPENAI_API_KEY=<your-venice-api-key>
OPENAI_BASE_URL=https://api.venice.ai/api/v1
EMBEDDING_PROVIDER=local
AGENTMEMORY_AUTO_COMPRESS=true
AGENTMEMORY_INJECT_CONTEXT=true
CONSOLIDATION_ENABLED=true
GRAPH_EXTRACTION_ENABLED=true
III_REST_PORT=3111
III_STREAMS_PORT=3112
```

Key points:
- **OPENAI_API_KEY** must be the full Venice key (starts with
  `VENICE_ADMIN_KEY_...`)
- **OPENAI_BASE_URL** must be `https://api.venice.ai/api/v1`
- **EMBEDDING_PROVIDER=local** avoids needing a separate embedding key;
  agentmemory uses Xenova/all-MiniLM-L6-v2 locally (384-dim vectors)
- All 4 LLM-backed feature flags can be enabled since Venice provides
  chat completions

## Detecting the Provider

agentmemory's `doctor` check reports the provider as `openai` (it
detects OPENAI_API_KEY presence). All LLM-backed features work:
compression, consolidation, graph extraction.

The `agentmemory doctor` output shows:

```
✓ LLM provider
✓ Embedding provider
✓ Knowledge graph extraction
✓ Memory consolidation
✓ LLM-powered observation compression
✓ In-conversation context injection
```

## Pitfall: .env Key Redaction

When using `write_file` or `patch` tools, the Venice API key may be
redacted from terminal output. Write the `.env` via terminal using
Python or heredoc to ensure the full key lands in the file.

```bash
python3 -c "
key = 'VENICE_ADMIN_KEY_xxxxxxxxxx'
content = f'''OPENAI_API_KEY={key}
OPENAI_BASE_URL=https://api.venice.ai/api/v1
...
'''
with open('/home/kubuntux/.agentmemory/.env', 'w') as f:
    f.write(content)
"
```

## Wrapper Script with Full Paths

For persistent startup, the wrapper script at
`~/.local/bin/agentmemory-start` should use full paths to survive
broken-PATH environments:

```bash
#!/bin/bash
cd ~/.agentmemory
set -a
source .env
set +a
exec /home/kubuntux/.npm-global/bin/agentmemory "$@"
```

Without full paths, `agentmemory status` or `source .env` may fail in
non-interactive terminal sessions where `agentmemory` isn't on PATH.
