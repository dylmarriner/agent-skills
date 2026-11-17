# Nexus Agent Handoff

Use nexus to pass context between agents (Hermes, OpenCode, PI, OpenClaw).

## Save handoff
```
memory_save(
  content="Handoff from Hermes to OpenCode: {context_summary}",
  agent_id="opencode:kubuntu-desktop",
  importance=0.9,
  tags=["handoff", "context-transfer"],
  metadata={"source": "hermes", "target": "opencode", "device": "kubuntu-desktop"}
)
```

## Read handoff at start
```
memory_recall(query="handoff from *", agent_id="opencode:kubuntu-desktop", limit=5)
agent_context(agent_id="opencode:kubuntu-desktop")
```
