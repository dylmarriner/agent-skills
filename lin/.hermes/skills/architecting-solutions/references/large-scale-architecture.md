# Large-Scale System Architecture — AIOS

This is the complete architecture reference for the AIOS (Autonomous AI Operating System) project — a cross-platform agent orchestration system controlling Android, Windows, macOS, and Linux devices.

## Language Strategy

| Where | Language | Why |
|-------|----------|-----|
| Core runtime (hot path) | Rust | Zero-GC, native everywhere, memory safety for sub-ms tool dispatch |
| AI/reasoning (cold path) | Python | Ecosystem depth (PyTorch, DSPy, LangChain). Inference latency dominates. |
| Mobile client | Kotlin | Native MediaProjection, AccessibilityService, foreground services |
| Desktop control UI | Flutter | Single codebase for Linux/Win/macOS dashboard |
| Developer ecosystem (MCP SDK) | TypeScript | npm community, plugin developers prefer TS |
| Cloud infrastructure | Go | Goroutine-per-connection for CRUD services. Fast compile. |

## Subsystem Allocation

| Subsystem | Lang | Lines | Key Implementation |
|-----------|------|-------|-------------------|
| Agent runtime loop | Rust | planned | Tokio async, sub-ms tool dispatch, session management |
| Model routing | Python | ~3K | Provider abstraction (OpenAI, OpenRouter, LiteLLM), router by task type x cost tier |
| Memory system | Python | ~4K | Working (TTL), episodic (numpy cosine), semantic (networkx graph), procedural (YAML templates) |
| Workflow engine | Python | ~1K | YAML DAG execution, cron scheduler, parallel step executor |
| Event bus | Python | ~1K | Async pub/sub with fnmatch wildcards, ring buffer history |
| MCP host | Python | ~1.5K | stdio/WebSocket/HTTP transport, process lifecycle, sandbox ACLs |
| Multi-agent swarm | Python | ~2.5K | Task routing (4 strategies), consensus engine, 10 specialist profiles |
| Web dashboard | TypeScript | ~3.4K | Next.js 15, device mgmt, workflow builder, settings |
| Android app | Kotlin | ~4.3K | Screen capture (MediaProjection), UI targeting (3-tier), WebRTC streaming, MCP server |
| Linux adapter | Python | ~2.5K | PipeWire/X11 capture, AT-SPI a11y, uinput injection, VA-API encode |
| Windows adapter | Python | ~1.8K | DXGI duplication, UIAutomation, Win32 SendInput |
| macOS adapter | Python | ~3.3K | CoreGraphics stream, AXUIElement, CGEvent, TCC permissions |
| Fleet management | Go | skeleton | Device enrollment, policy engine, compliance scoring |
| CI/CD | YAML | ~1K | 16-job matrix build, K8s deploy, cosign signing |

## Key Architecture Decisions

1. **Rust owns hot paths** — agent loop, encoder, WebRTC streaming, CRDT sync
2. **Python owns cold paths** — model routing, reasoning, memory consolidation
3. **Go owns CRUD services** — fleet management, API gateway, identity
4. **MCP as universal plugin protocol** — every tool is an MCP tool
5. **PostgreSQL + pgvector** — single database for relational + vector + JSONB
6. **WebRTC for streaming** — ICE/STUN/TURN + adaptive bitrate + DTLS
7. **CRDT for sync** — conflict-free merging without central server
8. **WASM for plugin execution** — deterministic sandboxing via wasmtime

## Architecture Document

The complete 10-section architecture analysis is at `AIOS-ARCHITECTURE.md` in the project root.
