# Nexus Memory Skill

Nexus is the unified cross-agent memory server at http://100.93.75.87:7777.
All agents share the same memory pool — save and recall across Hermes, OpenCode, PI, OpenClaw.

## Available Tools (via nexus-memory MCP)

### SAVE
```
memory_save(content, agent_id?, importance?, tags?, metadata?)
  - content: what to remember (required)
  - agent_id: scoped to agent (default: "default")
  - importance: 0.0-1.0 (default: 0.5)
  - tags: list of strings for categorization
  - metadata: dict with device, hostname, source, model, workspace, capabilities
```

### RECALL
```
memory_recall(query, agent_id?, limit?, memory_types?, search_modes?)
  - query: search text (required)
  - limit: results count (default: 10)
  - memory_types: filter by "world", "experience", "observation", "preference"
  - search_modes: "vector", "lexical", "graph", "temporal" (uses all 4 by default)
```

### REFLECT
```
memory_reflect(query, agent_id?, context?, depth?)
  - query: what to synthesize/reflect on
  - depth: "low", "mid", "high"
  - Returns structured insights, patterns, conclusions
```

### AGENT CONTEXT
```
agent_context(agent_id, tokens?)
  - Returns LLM-generated agent representation, recent memories, conclusions
  - tokens: budget for context window (default: 2000)
```

### AGENT LEARN
```
agent_learn(content)
  - Teach an agent something immediately
```

### NEXUS STATUS
```
nexus_status()
  - Health check with component status (postgres, redis, embeddings, LLM)
```

## Memory Types
| Type | When to Use |
|------|-------------|
| `world` | Facts about the world, project, system |
| `experience` | Things that happened during work |
| `observation` | Things noticed during work |
| `preference` | User choices, habits, preferred ways |

## Best Practices
- Always include metadata: device, hostname, source, model
- Use agent_context at start of sessions to pick up where you left off
- Save lessons after corrections with importance=0.8+
- Use memory_recall before starting non-trivial work
- Cross-agent: memory saved by one agent is visible to all
