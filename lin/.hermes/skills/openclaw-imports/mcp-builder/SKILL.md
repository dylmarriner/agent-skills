---
name: mcp-builder
description: Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK).
license: Complete terms in LICENSE.txt
---

# MCP Server Development Guide

## Overview

Create MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. The quality of an MCP server is measured by how well it enables LLMs to accomplish real-world tasks.

---

# Process

## 🚀 High-Level Workflow

Creating a high-quality MCP server involves four main phases:

### Phase 1: Deep Research and Planning

#### 1.1 Understand Modern MCP Design

**API Coverage vs. Workflow Tools:**
Balance comprehensive API endpoint coverage with specialized workflow tools. Workflow tools can be more convenient for specific tasks, while comprehensive coverage gives agents flexibility to compose operations. Performance varies by client—some clients benefit from code execution that combines basic tools, while others work better with higher-level workflows. When uncertain, prioritize comprehensive API coverage.

**Tool Naming and Discoverability:**
Clear, descriptive tool names help agents find the right tools quickly. Use consistent prefixes (e.g., `github_create_issue`, `github_list_repos`) and action-oriented naming.

**Context Management:**
Agents benefit from concise tool descriptions and the ability to filter/paginate results. Design tools that return focused, relevant data. Some clients support code execution which can help agents filter and process data efficiently.

**Actionable Error Messages:**
Error messages should guide agents toward solutions with specific suggestions and next steps.

#### 1.2 Study MCP Protocol Documentation

**Navigate the MCP specification:**

Start with the sitemap to find relevant pages: `https://modelcontextprotocol.io/sitemap.xml`

Then fetch specific pages with `.md` suffix for markdown format (e.g., `https://modelcontextprotocol.io/specification/draft.md`).

Key pages to review:
- Specification overview and architecture
- Transport mechanisms (streamable HTTP, stdio)
- Tool, resource, and prompt definitions

#### 1.3 Study Framework Documentation

**Recommended stack:**
- **Language**: TypeScript (high-quality SDK support and good compatibility in many execution environments e.g. MCPB. Plus AI models are good at generating TypeScript code, benefiting from its broad usage, static typing and good linting tools)
- **Transport**: Streamable HTTP for remote servers, using stateless JSON (simpler to scale and maintain, as opposed to stateful sessions and streaming responses). stdio for local servers.

**Load framework documentation:**

- **MCP Best Practices**: [📋 View Best Practices](./reference/mcp_best_practices.md) - Core guidelines

**For TypeScript (recommended):**
- **TypeScript SDK**: Use WebFetch to load `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`
- [⚡ TypeScript Guide](./reference/node_mcp_server.md) - TypeScript patterns and examples

**For Python:**
- **Python SDK**: Use WebFetch to load `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- [🐍 Python Guide](./reference/python_mcp_server.md) - Python patterns and examples

#### 1.4 Plan Your Implementation

**Understand the API:**
Review the service's API documentation to identify key endpoints, authentication requirements, and data models. Use web search and WebFetch as needed.

**Tool Selection:**
Prioritize comprehensive API coverage. List endpoints to implement, starting with the most common operations.

---

### Phase 2: Implementation

#### 2.1 Set Up Project Structure

See language-specific guides for project setup:
- [⚡ TypeScript Guide](./reference/node_mcp_server.md) - Project structure, package.json, tsconfig.json
- [🐍 Python Guide](./reference/python_mcp_server.md) - Module organization, dependencies

#### 2.2 Implement Core Infrastructure

Create shared utilities:
- API client with authentication
- Error handling helpers
- Response formatting (JSON/Markdown)
- Pagination support

#### 2.3 Implement Tools

For each tool:

**Input Schema:**
- Use Zod (TypeScript) or Pydantic (Python)
- Include constraints and clear descriptions
- Add examples in field descriptions

**Output Schema:**
- Define `outputSchema` where possible for structured data
- Use `structuredContent` in tool responses (TypeScript SDK feature)
- Helps clients understand and process tool outputs

**Tool Description:**
- Concise summary of functionality
- Parameter descriptions
- Return type schema

**Implementation:**
- Async/await for I/O operations
- Proper error handling with actionable messages
- Support pagination where applicable
- Return both text content and structured data when using modern SDKs

**Annotations:**
- `readOnlyHint`: true/false
- `destructiveHint`: true/false
- `idempotentHint`: true/false
- `openWorldHint`: true/false

---

### Phase 3: Review and Test

#### 3.1 Code Quality

Review for:
- No duplicated code (DRY principle)
- Consistent error handling
- Full type coverage
- Clear tool descriptions

#### 3.2 Build and Test

**TypeScript:**
- Run `npm run build` to verify compilation
- Test with MCP Inspector: `npx @modelcontextprotocol/inspector`

**Python:**
- Verify syntax: `python -m py_compile your_server.py`
- Test with MCP Inspector

See language-specific guides for detailed testing approaches and quality checklists.

---

### Phase 4: Create Evaluations

After implementing your MCP server, create comprehensive evaluations to test its effectiveness.

**Load [✅ Evaluation Guide](./reference/evaluation.md) for complete evaluation guidelines.**

#### 4.1 Understand Evaluation Purpose

Use evaluations to test whether LLMs can effectively use your MCP server to answer realistic, complex questions.

#### 4.2 Create 10 Evaluation Questions

To create effective evaluations, follow the process outlined in the evaluation guide:

1. **Tool Inspection**: List available tools and understand their capabilities
2. **Content Exploration**: Use READ-ONLY operations to explore available data
3. **Question Generation**: Create 10 complex, realistic questions
4. **Answer Verification**: Solve each question yourself to verify answers

#### 4.3 Evaluation Requirements

Ensure each question is:
- **Independent**: Not dependent on other questions
- **Read-only**: Only non-destructive operations required
- **Complex**: Requiring multiple tool calls and deep exploration
- **Realistic**: Based on real use cases humans would care about
- **Verifiable**: Single, clear answer that can be verified by string comparison
- **Stable**: Answer won't change over time

#### 4.4 Output Format

Create an XML file with this structure:

```xml
<evaluation>
  <qa_pair>
    <question>Find discussions about AI model launches with animal codenames. One model needed a specific safety designation that uses the format ASL-X. What number X was being determined for the model named after a spotted wild cat?</question>
    <answer>3</answer>
  </qa_pair>
<!-- More qa_pairs... -->
</evaluation>
```

---

### Phase 5: Multi-Platform Distribution — Plugins, SDKs & Client Configs

After building the MCP server, create distributable packages so agents on various platforms can consume it.

#### 5.1 Project Structure Pattern

Keep the MCP server as the root of a self-contained project. Any plugins for host platforms (OpenClaw, Hermes, Paperclip, etc.) live INSIDE this project as distributable packages — do NOT build them directly into the host platform's source tree.

Recommended layout:
```
my-mcp-project/
├── server.py                    # MCP server (the core)
├── README.md
├── .venv/
├── plugins/
│   ├── openclaw-my-mcp/         ← Standalone npm package, installable into OpenClaw
│   ├── hermes-my-mcp/           ← Python plugin package, installable into Hermes
│   └── paperclip-my-mcp/        ← TypeScript worker, installable into Paperclip
├── ides/                        ← IDE MCP config files
│   ├── windsurf/mcp_config.json
│   ├── antigravity/mcp_config.json
│   ├── vscode/mcp_config.json
│   ├── install-to-ides.mjs      ← Script that adds the MCP server to all IDE configs
│   └── README.md
├── sdk/
│   ├── python/                  ← pip-installable Python SDK
│   └── typescript/              ← npm-publishable TypeScript SDK
├── client-configs/              ← Configs for non-plugin clients
│   ├── README.md
│   └── paperclip.json
├── systemd/                     ← Service files
│   └── my-mcp.service
└── scripts/
    └── install.sh               ← Full project installer
```

**CRITICAL: Do not build plugins into the host platform's source tree.** The OpenClaw `extensions/` directory is for plugins that ship with OpenClaw itself, not for your MCP server's companion plugin. Keep the plugin in your project's `plugins/` directory and provide an install script that copies it into the host platform when the user chooses to install it. This keeps your project self-contained and distributable.

#### 5.2 OpenClaw Plugin Architecture

See [📋 OpenClaw Plugin Pattern](./reference/openclaw-plugin-pattern.md) for the full pattern, but the high-level approach:

1. **manifest** (`openclaw.plugin.json`): Declares tool IDs, config schema, agent skills
2. **entry point** (`src/index.ts`): Calls `api.registerTool()` for each MCP endpoint
3. **MCP session management**: Each tool call opens an HTTP session to the MCP server, caches the session ID (TTL ~14 min), and forwards parameters
4. **config**: Server URL, API key, and defaults are configurable via OpenClaw's plugin config system
5. **agent guidance**: `api.on("before_prompt_build")` injects system context

Key details:
- Use `fetch()` directly (no MCP SDK needed — the plugin IS the client)
- Cache MCP sessions by server URL with TTL < 15 min
- Use `resolveLivePluginConfigObject()` to read live config at call time
- Format results as human-readable text for the agent, not raw JSON

#### 5.3 Hermes Plugin Architecture

See [📋 Hermes Plugin Pattern](./reference/hermes-plugin-pattern.md) for details. High-level:

Hermes plugins are **Python-only** and live at `~/.hermes/plugins/<name>//. They consist of:

1. **`plugin.yaml`** — Manifest with name, version, description, `provides_tools`, and `requires_env`
2. **`schemas.py`** — Tool JSON schemas that the LLM sees. Each schema is a plain Python dict following OpenAI tool format with detailed description fields.
3. **`tools.py`** — Handler functions. Each function receives `(args: dict, **kwargs)` and must return a JSON string. Handlers use `urllib.request` to make HTTP calls to the MCP server.

Workflow:
- Hermes discovers plugins automatically from `~/.hermes/plugins/<name>/`
- The `plugin.yaml` `provides_tools` list must match function names in `tools.py` AND schema names in `schemas.py`
- Since Hermes supports MCP natively via `mcp_servers` in config.yaml, a native plugin is optional — it provides better tool descriptions and error handling than raw MCP

#### 5.4 Paperclip Adapter Plugin Architecture

See [📋 Paperclip Plugin Pattern](./reference/paperclip-plugin-pattern.md) for details. High-level:

Paperclip plugins are TypeScript workers using `@paperclipai/plugin-sdk`. The plugin package:

1. **`package.json`** — npm package with `@paperclipai/plugin-sdk` dependency
2. **`src/worker.ts`** — Entry point using `definePlugin({ setup(ctx) { ... } })`
3. **`manifest.json`** — Declares tool names, descriptions, and parameter schemas

Key APIs: `ctx.tools.register()`, `ctx.logger.info()`, `ctx.events.on()`, `ctx.jobs.register()`

Install via `~/.paperclip/adapter-plugins.json`.

#### 5.5 IDE MCP Config Distribution

For IDEs that support MCP but not custom plugins:

| IDE | Config Path | Schema Key |
|-----|-------------|------------|
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | `mcpServers` |
| Antigravity | `~/.gemini/antigravity/mcp_config.json` | `mcpServers` |
| VS Code | `~/.vscode/mcp.json` | `servers` |

Use the `url`-style MCP config: `{ "url": "http://host:port/mcp", "timeout": 120 }`

The install script should: create dir if missing, read existing config, add/update the entry, write back, print the path.

#### 5.6 SDK Distribution

**Python SDK** (`sdk/python/`): pip-installable, `SynapseClient` class wrapping all tools, lifecycle hooks `client.on("memory.store", callback)`, session management, env-var config.

**TypeScript SDK** (`sdk/typescript/`): npm-installable, full type definitions, session caching, `fetch()`-based MCP calls, lifecycle hooks.

#### 5.7 Client Configuration

For platforms that don't support plugins: provide MCP config files in `client-configs/`.

#### 5.8 Systemd Service

Package a systemd service file in `systemd/` for production deployment.

---  

## Pitfalls

- **Don't build plugins into the host platform's repo.** Keep plugins as standalone packages in your project's `plugins/` directory. Ship an install script. The user decides where to install them.
- **Don't hardcode server URLs in plugins.** Use `openclaw.plugin.json` configSchema so the server URL is configurable. Default to a reasonable value but make it overridable.
- **MCP session TTL matters.** Plugin sessions expire after ~15 min. Cache the session ID but re-init if expired. Do not re-init on every tool call.
- **FastMCP API key redaction.** FastMCP v1.27+ auto-redacts fields named `api_key` AND values starting with sk_, syn-, tok_, key_, or secret_. Both conditions trigger independently. You must fix BOTH:
  1. Rename the JSON response field from `api_key` to `key` (or anything not matching the redaction patterns)
  2. Change the key value prefix from `sk_syn_` to something like `syn_` that doesn't match redaction patterns
  If you only rename the field but the value still starts with `sk_`, FastMCP truncates the value anyway. If you only change the prefix but the field is named `api_key`, FastMCP redacts it anyway. Both must change for the key to pass through intact.
- **Response formatting.** MCP servers return JSON to the plugin. The plugin should format results as human-readable text for the agent. Raw JSON dumps are hard for agents to parse — use structured text output with scores, counts, and relevant snippets.
- **Always format tool results.** After calling `callServer()` in a plugin, ALWAYS format the raw JSON into human-readable text. Don't dump `JSON.stringify(result)` into the response — the agent can't parse raw JSON as well as structured text.
- **Tool names must be unique per platform.** The same underlying MCP tool (`store`) gets different names per plugin: `synapse_store` in Hermes, `synapse_store` in OpenClaw, `synapse_store` in Paperclip. Use a consistent prefix namespace.
- **IDE MCP configs use different schema keys.** Windsurf/Antigravity use `mcpServers`; VS Code uses `servers`. Both accept `url`-style configs for remote HTTP MCP servers.

# Reference Files

## 📚 Documentation Library

Load these resources as needed during development:

### Core MCP Documentation (Load First)
- **MCP Protocol**: Start with sitemap at `https://modelcontextprotocol.io/sitemap.xml`, then fetch specific pages with `.md` suffix
- [📋 MCP Best Practices](./reference/mcp_best_practices.md) - Universal MCP guidelines including:
  - Server and tool naming conventions
  - Response format guidelines (JSON vs Markdown)
  - Pagination best practices
  - Transport selection (streamable HTTP vs stdio)
  - Security and error handling standards

### SDK Documentation (Load During Phase 1/2)
- **Python SDK**: Fetch from `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- **TypeScript SDK**: Fetch from `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`

### Language-Specific Implementation Guides (Load During Phase 2)
- [🐍 Python Implementation Guide](./reference/python_mcp_server.md) - Complete Python/FastMCP guide with:
  - Server initialization patterns
  - Pydantic model examples
  - Tool registration with `@mcp.tool`
  - Complete working examples
  - Quality checklist

- [⚡ TypeScript Implementation Guide](./reference/node_mcp_server.md) - Complete TypeScript guide with:
  - Project structure
  - Zod schema patterns
  - Tool registration with `server.registerTool`
  - Complete working examples
  - Quality checklist

### Evaluation Guide (Load During Phase 4)
- [📋 IDE VS Code Extension Pattern](./reference/ide-vscode-extension-pattern.md) — Full VS Code extension with commands, status bar, sidebar, IDE auto-detection, and webview results
- [✅ Evaluation Guide](./reference/evaluation.md) - Complete evaluation creation guide with:
  - Question creation guidelines
  - Answer verification strategies
  - XML format specifications
  - Example questions and answers
  - Running an evaluation with the provided scripts
