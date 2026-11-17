# Honcho Memory Skill

Honcho is the primary memory backend for Nexus. It provides AI-native memory with session persistence, cross-session search, and conversation memory management.

## Capabilities

### Automatic Memory Operations
Honcho automatically:
- **Retains conversations** — Every interaction is stored as a memory in Honcho's knowledge graph
- **Recalls context** — Relevant past conversations are injected into the system prompt before each turn
- **Cross-session search** — By default, searches across all sessions in the workspace

### Memory Types
Honcho stores memory in a graph structure:
- **Sessions** — Individual conversations organized per user/channel
- **Messages** — Each message in a session
- **Metamessages** — User/agent messages with metadata
- **Documents** — Rich knowledge documents that can be created and searched

## Configuration

Honcho is configured via `plugins.entries.openclaw-honcho.config`:
- API key: stored in the config
- Workspace: "openclaw" (default)
- Base URL: `https://api.honcho.dev`
- `allowConversationAccess`: `true` — enables access to conversation history
- `crossSessionSearch`: `true` — search across all sessions

## Autonomous Usage

### Auto-triggered Behaviors
Honcho automatically:
1. **Stores** every conversation turn as memory
2. **Retrieves** relevant context from past conversations
3. **Persists** session state across restarts

### Manual Memory Operations
You can use Honcho for:
1. **Session queries** — Ask Honcho about past conversations
2. **Knowledge retrieval** — Search stored documents and facts
3. **Cross-context recall** — Connect information across different channels

## Integration

- **Primary memory slot**: Honcho fills the `memory` plugin slot
- **Works with Hindsight**: Both memory systems work together — Honcho handles conversational memory, Hindsight handles biomimetic long-term memory with fact extraction
- **Works with openclawbrain**: Brain plugin provides additional cognitive capabilities alongside Honcho memory

## Troubleshooting

- If memory seems empty, check that Honcho API key is valid
- If cross-session search isn't working, verify `crossSessionSearch` config is `true`
- Messages containing noise patterns (HEARTBEAT_OK, etc.) are automatically filtered
