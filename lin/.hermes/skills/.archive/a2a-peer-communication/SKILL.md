---
name: a2a-peer-communication
description: "Use when chatting with remote A2A agents. Test reachability."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [a2a, agent-to-agent, peer, communication, hermes]
---

# A2A Peer Communication

## When to Use

Use when the user asks to set up agent-to-agent chat, inspect configured peers, or message remote agents.

## Procedure

1. Load the A2A tool capability and inspect peers with `a2a_list`; do not assume a tool/schema or peer setup from memory.
2. For setup, establish intended peer names/endpoints, then inspect the live `a2a_agents` block in `~/.hermes/config.yaml` and compare it with `a2a_list` output. Preserve existing settings and secrets; only add or correct the minimum missing entries.
3. Apply peer entries only through the documented config surface. Keep every peer mapping nested under the top-level `a2a_agents:` key; do not append entries at the file end, where they may land beneath another YAML section/commented example and become ineffective. After edits, inspect the surrounding YAML structure and validate parsing/config loading before testing.
4. Test each intended peer independently with a short, harmless `a2a_call`. Report success/failure per peer; a configured peer is not necessarily reachable.
5. For an ongoing exchange, retain and reuse the returned `context_id`. For discovery of an unknown endpoint, use `a2a_discover` before messaging when useful.
6. Keep the result concise: state what was already configured, which test replies were received, and any unreachable peer without claiming setup is complete for that peer.

## Pitfalls

- Verify an actual request/reply before saying chat works; listing a peer proves configuration only, not service availability.
- Distinguish connection refusal from missing configuration; do not invent a fix or claim remote service was started when the call failed.
- Send separate calls to local A2A tools unless the invocation surface explicitly supports batching; connector-only batch support does not imply local-tool batching.
- Do not conflate A2A peer chat with Hermes `delegate_task`: A2A addresses remote peer agents, while delegation spawns an isolated child task.
