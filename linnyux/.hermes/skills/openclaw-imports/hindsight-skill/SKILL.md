# Hindsight Memory Skill

Hindsight is a biomimetic long-term memory plugin for Nexus. It provides intelligent fact extraction, memory consolidation, and context-aware recall using a local embedding daemon.

## Capabilities

### Automatic Memory Operations
Hindsight automatically:
- **Retains conversations** — Extracts facts and memories after each turn using LLM-powered extraction
- **Recalls context** — Injects relevant memories into system prompt before each turn
- **Memory consolidation** — Periodically consolidates observations into knowledge

### Memory Types
Hindsight uses a biomimetic memory model:
- **World** — Factual knowledge about the world and user
- **Experience** — Episodic memories from past conversations
- **Observation** — Synthesized insights from multiple conversations

### Knowledge Tools (when enabled)
When `enableKnowledgeTools: true`, Hindsight exposes:
- `agent_knowledge_list_pages` — List all knowledge pages
- `agent_knowledge_get_page` — Get a specific knowledge page
- `agent_knowledge_create_page` — Create a new knowledge page
- `agent_knowledge_update_page` — Update an existing knowledge page
- `agent_knowledge_delete_page` — Delete a knowledge page
- `agent_knowledge_recall` — Recall relevant memories
- `agent_knowledge_ingest` — Ingest a document into memory

## Configuration

Configured via `plugins.entries.hindsight-openclaw.config`:

### LLM Provider (for memory extraction)
```json
{
  "llmProvider": "openai",
  "llmModel": "deepseek-chat",
  "llmBaseUrl": "https://api.deepseek.com",
  "llmApiKey": { "source": "env", "id": "DEEPSEEK_API_KEY" }
}
```

### Memory Settings
- `dynamicBankId`: `true` — Isolate memories per user/channel
- `autoRecall`: `true` — Auto-inject memories before each turn
- `autoRetain`: `true` — Auto-retain after each turn
- `recallBudget`: `"mid"` — Balance between speed and recall quality
- `recallTypes`: `["world", "experience"]` — Focus on facts and experiences
- `recallMaxTokens`: `1024` — Memory context budget per turn

### Daemon Settings
- `apiPort`: `9077` — Local daemon API port
- `embedPort`: `0` — Auto-assign embed server port
- `daemonIdleTimeout`: `0` — Never timeout

## Autonomous Usage

### Auto-triggered Behaviors
Hindsight automatically handles:
1. **Fact extraction** — Extracts structured facts from conversations
2. **Context injection** — Injects relevant memories before each response
3. **Memory isolation** — Keeps memories separate per user/channel
4. **Exclusion** — Ignores heartbeat sessions by default

### Knowledge Management
You can tell me to:
1. "Remember that Dylan prefers dark mode" — Hindsight extracts the fact
2. "Search your memory for X" — Recall relevant experiences
3. "Create a knowledge page about project MUTS" — Build persistent knowledge

### Memory Tags
You can add metadata tags to retained memories by including `<retain_tags>tag1,tag2</retain_tags>` in messages.

## Integration

- **Works with Honcho**: Both memory systems coexist — Honcho handles conversational memory while Hindsight provides deeper fact extraction and consolidation
- **Local Daemon**: Hindsight runs a local `hindsight-embed` daemon on port 9077
- **Dynamic Banks**: Each user/channel gets an isolated memory bank

## Troubleshooting

- If recall seems empty, ensure DEEPSEEK_API_KEY env var is set
- Check daemon status: `curl http://localhost:9077/health`
- If daemon fails to start, check `~/.openclaw/data/hindsight*.log`
- Increase `recallBudget` to `"high"` for better recall quality
- Set `debug: true` in config for verbose logging

## Best Practices

- Use memory tags to organize information: `<retain_tags>project:muts,priority:high</retain_tags>`
- Dynamic banks keep user data isolated — good for multi-user setups
- Exclude noisy channels via `excludeProviders` config
