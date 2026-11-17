---
name: python-mcp-server-generator
description: 'Generate a complete MCP server project in Python with tools, resources, and proper configuration'
---

# Generate Python MCP Server

Create a complete Model Context Protocol (MCP) server in Python with the following specifications:

## Requirements

1. **Project Structure**: Create a new Python project with proper structure using uv
2. **Dependencies**: Include mcp[cli] package with uv
3. **Transport Type**: Choose between stdio (for local) or streamable-http (for remote)
4. **Tools**: Create at least one useful tool with proper type hints
5. **Error Handling**: Include comprehensive error handling and validation

## Implementation Details

### Project Setup
- Initialize with `uv init project-name`
- Add MCP SDK: `uv add "mcp[cli]"`
- Create main server file (e.g., `server.py`)
- Add `.gitignore` for Python projects
- Configure for direct execution with `if __name__ == "__main__"`

### Server Configuration
- Use `FastMCP` class from `mcp.server.fastmcp`
- Set server name and optional instructions
- Choose transport: stdio (default) or streamable-http
- For HTTP: optionally configure host, port, and stateless mode

### Tool Implementation
- Use `@mcp.tool()` decorator on functions
- Always include type hints - they generate schemas automatically
- Write clear docstrings - they become tool descriptions
- Use Pydantic models or TypedDicts for structured outputs
- Support async operations for I/O-bound tasks
- Include proper error handling

### Resource/Prompt Setup (Optional)
- Add resources with `@mcp.resource()` decorator
- Use URI templates for dynamic resources: `"resource://{param}"`
- Add prompts with `@mcp.prompt()` decorator
- Return strings or Message lists from prompts

### Code Quality
- Use type hints for all function parameters and returns
- Write docstrings for tools, resources, and prompts
- Follow PEP 8 style guidelines
- Use async/await for asynchronous operations
- Implement context managers for resource cleanup
- Add inline comments for complex logic

## Example Tool Types to Consider
- Data processing and transformation
- File system operations (read, analyze, search)
- External API integrations
- Database queries
- Text analysis or generation (with sampling)
- System information retrieval
- Math or scientific calculations

## Configuration Options
- **For stdio Servers**:
  - Simple direct execution
  - Test with `uv run mcp dev server.py`
  - Install to Claude: `uv run mcp install server.py`
  
- **For HTTP Servers**:
  - Port configuration via environment variables
  - Stateless mode for scalability: `stateless_http=True`
  - JSON response mode: `json_response=True`
  - CORS configuration for browser clients
  - Mounting to existing ASGI servers (Starlette/FastAPI)

## Testing Guidance
- Explain how to run the server:
  - stdio: `python server.py` or `uv run server.py`
  - HTTP: `python server.py` then connect to `http://localhost:PORT/mcp`
- Test with MCP Inspector: `uv run mcp dev server.py`
- Install to Claude Desktop: `uv run mcp install server.py`
- Include example tool invocations
- Add troubleshooting tips

## Additional Features to Consider
- Context usage for logging, progress, and notifications
- LLM sampling for AI-powered tools
- User input elicitation for interactive workflows
- Lifespan management for shared resources (databases, connections)
- Structured output with Pydantic models
- Icons for UI display
- Image handling with Image class
- Completion support for better UX

## Production Patterns

### Multi-Tenant MCP Server Design

For production MCP servers serving multiple clients/teams:

- Add a `tenants` table with `tenant_id`, `api_key`, `tier`, `status`, and limit columns
- Scope ALL data tables with `tenant_id` (every query adds `WHERE tenant_id=?`)
- Validate API keys via a `validate_tenant_key()` function that checks the tenants table
- Store tier-based limits (max devices, max memories, max storage) in the tenant record
- Register devices with Tailscale IP binding for secure mesh networking
- See `references/production-patterns.md` for the full multi-tenant schema and auth middleware pattern

### FastMCP v1.27.1 API Key Redaction

FastMCP v1.27.1 automatically redacts fields named `api_key`, `key`, `secret`,
`token`, `password` in both `content[0].text` and `structuredContent` responses.
Values matching patterns like `sk_` are truncated to `***` or `sk_...abc`.

**Workarounds:**
- Change the API key prefix from `sk_` to something that doesn't trigger redaction (e.g. `syn_`, `se_`)
- Return the key in a message string field alongside a non-redacted field name (e.g. `"credential": api_key` instead of `"api_key"`)
- Or disable structured content redaction entirely (SDK-specific, not always available)

### Streamable HTTP Session Management

The `streamable-http` transport requires session initialization:

```python
# Client sends:
{"jsonrpc":"2.0","id":1,"method":"initialize",
 "params":{"protocolVersion":"2025-03-26","capabilities":{},
           "clientInfo":{"name":"my-client","version":"1.0"}}}
# Server responds with header: mcp-session-id: <uuid>
# Subsequent requests include: Mcp-Session-Id: <uuid>
```

Each tool call requires a fresh or cached session. Sessions are maintained
server-side so clients can reuse them across multiple calls.

### FTS5 for Contentless MCP Servers

When using FTS5 in a database-backed MCP server — the table MUST use
`content=''` for contentless mode, and indexing is done manually:

```python
con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS my_fts USING fts5(..., content='')")
# Insert: INSERT INTO my_fts(...) VALUES (...)
# Delete: INSERT INTO my_fts(my_fts, id) VALUES ('delete', ?)
# Triggers do NOT work with contentless tables — manage indexing in tool code
```

### Hybrid Retrieval Pipeline for MCP Tools

Combine FTS5 keyword search with embedding-based vector search:

```python
# 1. Try FTS5 exact/keyword match first
# 2. If embeddings enabled, compute query embedding and cosine-similarity
# 3. Fall back to per-word LIKE matching for non-FTS queries
# 4. RRF-fuse results from all three sources
```

Per-word LIKE matching avoids the problem of exact-phrase LIKE failing on
reordered or separated query terms.

### Production Deployment

- Use systemd user services with environment variable configuration
- Enable Tailscale auto-detection for private mesh networking
- Configure SQLite with WAL mode, busy_timeout, and synchronous=NORMAL
- Set up audit logging as an append-only table (SOC2 readiness)
- Expose health endpoint returning DB stats, Tailscale IP, version
- See `templates/systemd.service` for a production service template

## Reference Files
- `references/production-patterns.md` — Multi-tenant schema, auth middleware, deployment patterns
- `templates/systemd.service` — systemd user service template

## Best Practices
- Use type hints everywhere - they're not optional
- Return structured data when possible
- Log to stderr (or use Context logging) to avoid stdout pollution
- Clean up resources properly
- Validate inputs early
- Provide clear error messages
- Test tools independently before LLM integration
- For multi-tenant servers, always validate API keys on every tool invocation
- Use vector clocks for conflict resolution in distributed sync scenarios
- Store embeddings as BLOBs (np.float32.tobytes()) for vector search integration

Generate a complete, production-ready MCP server with type safety, proper error handling, and comprehensive documentation.
