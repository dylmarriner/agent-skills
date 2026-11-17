# OpenClaw MCP Bridge — Tool Inventory

The OpenClaw bridge (`openclaw-direct-bridge.ts`) exposes every OpenClaw built-in tool plus plugins through a single tunnel profile (`openclaw-tools`). Each tool is prefixed with the machine hostname (e.g. `kubuntux_`) to support multi-device aggregation.

**Source**: `/media/kubuntux/DEVELOPMENT1/openclaw/src/mcp/openclaw-direct-bridge.ts`
**Bridge logic**: `createOpenClawCodingTools()` (base + file ops) + `createOpenClawTools()` (agent/web/media) + bridge extras + plugin tools.

## Tool Categories

### 🖥️ System & File Operations (base coding tools)
| Exposed as | Description |
|---|---|
| `kubuntux_exec` | Sandboxed shell execution |
| `kubuntux_process` | Process management (spawn, poll, kill) |
| `kubuntux_read` | Read files from workspace |
| `kubuntux_edit` | Find-and-replace file edits |
| `kubuntux_write` | Create/overwrite files |
| `kubuntux_apply_patch` | Bulk V4A patch application |

### 🧠 OpenClaw Agent Loop
| Exposed as | Description |
|---|---|
| `kubuntux_nodes` | Node tree orchestration (core flow system) |
| `kubuntux_cron` | Schedule/manage cron jobs |
| `kubuntux_gateway` | Dispatch to gateway subagents |
| `kubuntux_agents_list` | List available agents |
| `kubuntux_subagents` | Manage subagents |
| `kubuntux_sessions_list` | List active sessions |
| `kubuntux_sessions_history` | Session history |
| `kubuntux_sessions_spawn` | Spawn background subagents |
| `kubuntux_sessions_send` | Send messages through channels |
| `kubuntux_sessions_yield` | Yield session for subagent |
| `kubuntux_session_status` | Get session status |
| `kubuntux_skill_workshop` | Manage/workshop skills |

### 🎯 Goals & Planning
| Exposed as | Description |
|---|---|
| `kubuntux_get_goal` | Read current goal |
| `kubuntux_create_goal` | Create/set goal |
| `kubuntux_update_goal` | Update goal |
| `kubuntux_update_plan` | Update execution plan |

### 📡 Web & Media Generation
| Exposed as | Description |
|---|---|
| `kubuntux_web_search` | Web search |
| `kubuntux_web_fetch` | Fetch/extract page content |
| `kubuntux_image_generate` | AI image generation |
| `kubuntux_music_generate` | AI music generation |
| `kubuntux_video_generate` | AI video generation |
| `kubuntux_image` | Image analysis/processing |
| `kubuntux_pdf` | PDF handling |

### 🔊 Communication
| Exposed as | Description |
|---|---|
| `kubuntux_message` | Send messages through channels |
| `kubuntux_tts` | Text-to-speech |
| `kubuntux_heartbeat` | Heartbeat response tool |
| `kubuntux_transcripts` | Transcript handling |

### 🔌 Escape Hatches (bridge-specific, not in normal agent tools)
| Exposed as | Description |
|---|---|
| `kubuntux_system_exec` | **Raw unrestricted shell** — no sandbox, no security checks. Full filesystem/network/device access. |
| `kubuntux_openclaw_ask` | **Full agent spawn** — runs `openclaw agent --local` with its own model, agent loop, and complete toolset. Costs model tokens. |

### 🔧 Plugin Tools
Any installed OpenClaw plugins also appear as prefixed tools (dynamic, depends on what's loaded).

## Total ~35+ tools

Around 28 core tools (base + OpenClaw tools) + 2 escape hatches + any plugin tools.

## How to inspect this in a running tunnel

The bridge's health endpoint shows MCP metadata but not individual tool names. To see the actual live tool list, either:
1. Read the bridge source (`openclaw-direct-bridge.ts`) and trace `resolveAllTools()` → `createOpenClawCodingTools()` + `createOpenClawTools()` + `resolvePluginTools()`
2. Or connect through the tunnel and query the MCP `list_tools` capability (requires an OpenAI product like ChatGPT connected to the tunnel)
