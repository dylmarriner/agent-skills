---
name: mcp-server-generator
description: Complete toolkit for creating MCP (Model Context Protocol) servers across multiple programming languages. Use when building MCP servers in Python, TypeScript, Go, Rust, Java, C#, Kotlin, PHP, Swift, Ruby, or any supported language. Includes all language-specific patterns, templates, and best practices.
license: MIT
---

# MCP Server Generator Toolkit

Complete toolkit for creating Model Context Protocol (MCP) servers across all major programming languages. These patterns are tested across production MCP implementations.

## When to Use

**Triggers:**
- Building MCP servers
- Creating tools for AI agents
- Implementing resources and prompts
- Multi-language MCP server development
- MCP server debugging and deployment

**Context:**
- All MCP server implementations (13+ languages)
- Agent tool development
- AI integration patterns
- Server-hosted AI tools

---

## Table of Contents

### Language-Specific Generators

1. [Python MCP Server](#python-mcp-server)
2. [TypeScript MCP Server](#typescript-mcp-server)
3. [Go MCP Server](#go-mcp-server)
4. [Rust MCP Server](#rust-mcp-server)
5. [Java MCP Server](#java-mcp-server)
6. [C# MCP Server](#c-mcp-server)
7. [Kotlin MCP Server](#kotlin-mcp-server)
8. [PHP MCP Server](#php-mcp-server)
9. [Swift MCP Server](#swift-mcp-server)
10. [Ruby MCP Server](#ruby-mcp-server)

### Common Patterns

- [Tool Definition](#tool-definition)
- [Resource Implementation](#resource-implementation)
- [Prompt Templates](#prompt-templates)
- [Authentication & Authorization](#authentication--authorization)

---

## Python MCP Server

### Project Structure

```
python-mcp-server/
├── src/
│   ├── __init__.py
│   ├── server.py
│   ├── tools/
│   │   ├── __init__.py
│   │   └── my_tool.py
│   ├── resources/
│   │   └── my_resource.py
│   └── prompts/
│       └── my_prompt.py
├── tests/
├── pyproject.toml
└── README.md
```

### Basic Server Implementation

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("my-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="my_tool",
            description="Does something useful",
            inputSchema={
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                    "arg2": {"type": "integer"}
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "my_tool":
        result = f"Called with {arguments}"
        return [TextContent(type="text", text=result)]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## TypeScript MCP Server

### Project Structure

```
typescript-mcp-server/
├── src/
│   ├── index.ts
│   ├── server.ts
│   └── tools/
│       └── myTool.ts
├── package.json
└── tsconfig.json
```

### Basic Server Implementation

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";

const server = new Server({
  name: "my-server",
  version: "1.0.0"
}, {
  capabilities: {
    tools: {}
  }
});

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [{
      name: "myTool",
      description: "Does something useful",
      inputSchema: {
        type: "object",
        properties: {
          arg1: { type: "string" },
          arg2: { type: "number" }
        }
      }
    }]
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "myTool") {
    return {
      content: [{
        type: "text",
        text: `Called with ${JSON.stringify(request.params.arguments)}`
      }]
    };
  }
  throw new Error(`Unknown tool: ${request.params.name}`);
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(console.error);
```

---

## Go MCP Server

### Project Structure

```
go-mcp-server/
├── cmd/
│   └── server/
│       └── main.go
├── internal/
│   ├── server/
│   │   └── server.go
│   └── tools/
│       └── myTool.go
├── go.mod
└── README.md
```

### Basic Server Implementation

```go
package main

import (
    "context"
    "log"
    "os"
    
    "github.com/modelcontextprotocol/go-sdk/server"
    "github.com/modelcontextprotocol/go-sdk/types"
)

type myServer struct {
    server.Server
}

func (s *myServer) ListTools(ctx context.Context) ([]types.Tool, error) {
    return []types.Tool{
        {
            Name:        "myTool",
            Description: "Does something useful",
            InputSchema: types.JSONSchema{
                Type: "object",
                Properties: map[string]types.JSONSchema{
                    "arg1": {Type: "string"},
                    "arg2": {Type: "number"},
                },
            },
        },
    }, nil
}

func (s *myServer) CallTool(ctx context.Context, params types.CallToolParams) (*types.CallToolResult, error) {
    if params.Name != "myTool" {
        return nil, &types.Error{Code: -32601, Message: "Unknown tool"}
    }
    
    return &types.CallToolResult{
        Content: []types.Content{
            &types.TextContent{
                Text: fmt.Sprintf("Called with arguments: %v", params.Arguments),
            },
        },
    }, nil
}

func main() {
    s := &myServer{
        Server: *server.NewServer(&protocol.LanguageClient{}, &protocol.ServerOptions{
            Name:    "my-server",
            Version: "1.0.0",
        }),
    }
    
    s.AddToolHandler("myTool", s.CallTool)
}
```

---

## Rust MCP Server

### Project Structure

```
rust-mcp-server/
├── src/
│   ├── main.rs
│   ├── server.rs
│   └── tools/
│       └── mod.rs
├── Cargo.toml
└── README.md
```

### Basic Server Implementation

```rust
use mcp_server::{Server, ServerHandler, CallToolParams, CallToolResult};

struct MyServer;

#[mcp_server::server]
impl ServerHandler for MyServer {
    const NAME: &'static str = "my-server";
    const VERSION: &'static str = "1.0.0";
    
    fn list_tools(&self) -> Vec<Tool> {
        vec![Tool {
            name: "myTool".to_string(),
            description: "Does something useful".to_string(),
            input_schema: serde_json::json!({
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                    "arg2": {"type": "number"}
                }
            })
        }]
    }
    
    fn call_tool(&self, name: &str, arguments: serde_json::Value) -> Result<CallToolResult, Error> {
        match name {
            "myTool" => Ok(CallToolResult {
                content: vec![Content::Text {
                    text: format!("Called with: {}", arguments)
                }]
            }),
            _ => Err(Error::ToolNotFound)
        }
    }
}

fn main() {
    let server = MyServer;
    server.run().unwrap();
}
```

---

## Java MCP Server

### Project Structure

```
java-mcp-server/
├── src/
│   └── main/
│       └── java/
│           └── com.example/
│               ├── McpServerApp.java
│               └── tools/
│                   └── MyTool.java
├── pom.xml
└── README.md
```

### Basic Server Implementation

```java
package com.example;

import com.modelcontextprotocol.sdk.server.Server;
import com.modelcontextprotocol.sdk.server.ServerHandler;
import com.modelcontextprotocol.sdk.types.Tool;

public class McpServerApp {
    public static void main(String[] args) {
        Server server = new Server("my-server", "1.0.0");
        
        server.addTool(new Tool()
            .setName("myTool")
            .setDescription("Does something useful")
            .setInputSchema(JsonObject.builder()
                .add("type", "object")
                .add("properties", JsonObject.builder()
                    .add("arg1", JsonObject.builder().add("type", "string").build())
                    .add("arg2", JsonObject.builder().add("type", "number").build())
                ).build())
        );
        
        server.start();
    }
}
```

---

## C# MCP Server

### Project Structure

```
csharp-mcp-server/
├── src/
│   └── McpServer/
│       └── Program.cs
├── McpServer.csproj
└── README.md
```

### Basic Server Implementation

```csharp
using ModelContextProtocol.Server;
using ModelContextProtocol.Types;

var server = new Server("my-server", "1.0.0");

server.AddTool(new Tool
{
    Name = "myTool",
    Description = "Does something useful",
    InputSchema = new JsonObject
    {
        ["type"] = "object",
        ["properties"] = new JsonObject
        {
            ["arg1"] = new JsonObject { ["type"] = "string" },
            ["arg2"] = new JsonObject { ["type"] = "number" }
        }
    }
});

await server.RunAsync();
```

---

## Common Patterns Across All Languages

### Tool Definition

**Required Fields:**
- `name` - Unique identifier
- `description` - What the tool does
- `inputSchema` - JSON Schema for parameters

**Best Practices:**
- Use clear, descriptive names
- Document what each parameter does
- Validate input schemas carefully
- Handle errors gracefully

### Resource Implementation

**Resource Types:**
- Static resources (files, configs)
- Dynamic resources (API responses, computed values)
- Template resources (parameterized content)

**Resource URI Pattern:**
```
mcp://<server-name>/<resource-type>/<id>
```

Example: `mcp://files/user-profiles/123`

### Prompt Templates

**Prompt Structure:**
```json
{
  "name": "my-prompt",
  "description": "Generates a summary",
  "arguments": [
    {
      "name": "context",
      "description": "The context to summarize",
      "required": true
    }
  ]
}
```

### Authentication & Authorization

**Common Patterns:**

**1. API Key Authentication**
```python
@app.list_tools()
async def list_tools():
    # Check auth header
    api_key = request.headers.get("Authorization")
    if not api_key or not validate_api_key(api_key):
        raise AuthorizationError("Invalid API key")
    # ... rest of logic
```

**2. JWT Token Authentication**
```typescript
server.setRequestHandler(ListToolsRequestSchema, async (request, extra) => {
  const token = extra.authToken;
  if (!token || !validateJWT(token)) {
    throw new Error("Authentication required");
  }
  // ... proceed with tool
});
```

**3. OAuth Flow**
```go
func (s *myServer) CallTool(ctx context.Context, params types.CallToolParams) (*types.CallToolResult, error) {
    oauthToken, ok := ctx.Value(oauthKey).(string)
    if !ok || !validateOAuthToken(oauthToken) {
        return nil, &types.Error{Code: -32000, Message: "OAuth required"}
    }
    // ... proceed
}
```

---

## Security Best Practices

**1. Input Validation:**
- Validate all tool parameters
- Sanitize user input
- Check for injection attacks
- Enforce input length limits

**2. Authorization:**
- Implement proper auth checks
- Use least privilege principle
- Log all access attempts
- Rate limit requests

**3. Error Handling:**
- Don't leak sensitive information in errors
- Return appropriate error codes
- Log errors for debugging
- Provide user-friendly messages

**4. Resource Limits:**
- Set timeouts on operations
- Limit memory usage
- Prevent infinite loops
- Monitor resource consumption

---

## Deployment Patterns

### Containerized Deployment

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "src/server.py"]
```

### Serverless Deployment

**AWS Lambda:**
```json
{
  "Runtime": "python3.11",
  "Handler": "src.server.handler",
  "Environment": {
    "Variables": {
      "MCP_LOG_LEVEL": "INFO"
    }
  }
}
```

### Process Management

**SystemD Service:**
```ini
[Unit]
Description=MCP Server
After=network.target

[Service]
Type=simple
User=mcp
ExecStart=/usr/bin/python3 /opt/mcp-server/src/server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Testing Strategies

### Unit Tests

```python
@app.tool()
def my_tool(arg1: str, arg2: int) -> str:
    return f"{arg1}: {arg2}"

# Test
def test_my_tool():
    result = my_tool("test", 123)
    assert result == "test: 123"
```

### Integration Tests

```python
async def test_server_integration():
    async with create_test_server() as server:
        response = await server.call_tool("my_tool", {"arg1": "test", "arg2": 123})
        assert response.status == "success"
```

---

## Common Mistakes

**DON'T: Skip input validation**
```python
# BAD - No validation
async def my_tool(value):
    return result

# GOOD - Validate input
async def my_tool(value: str):
    if not value or not isinstance(value, str):
        raise ValueError("Value must be a non-empty string")
    return result
```

**DON'T: Ignore errors**
```python
# BAD - Silently swallowing errors
try:
    result = risky_operation()
except:
    pass

# GOOD - Log and handle errors
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    raise
```

**DON'T: Hardcode configuration**
```python
# BAD - Hardcoded values
API_KEY = "secret123"

# GOOD - Environment variables
API_KEY = os.getenv("API_KEY")
```

---

## Quick Reference

**Language Support Matrix:**
- ✅ Python - Full support, mature
- ✅ TypeScript - Full support, mature
- ✅ Go - Full support
- ✅ Rust - Full support
- ✅ Java - Full support
- ✅ C# - Full support
- ✅ Kotlin - Full support
- ✅ PHP - Full support
- ✅ Swift - Full support
- ✅ Ruby - Full support

**See also:**
- `references/windsurf-mcp-integration.md` — connecting MCP servers to Windsurf IDE's Cascade agent.
- `references/codex-cli-mcp-setup.md` — Codex CLI MCP config format differences, streamable HTTP permission bug in v0.142.x, and the stdio proxy workaround.

**Core Components:**
- Tools - Functions AI can call
- Resources - Data AI can access
- Prompts - Templates AI can use

**Protocol Versions:**
- MCP 1.0 - Current stable
- MCP 2.0 - In development

**Transport Options:**
- Stdio
- HTTP/SSE
- WebSocket
- TCP

---

*Comprehensive MCP server generation toolkit consolidating all language-specific MCP server development patterns across Python, TypeScript, Go, Rust, Java, C#, Kotlin, PHP, Swift, Ruby, and more. All MCP server generator skills merged into one class-level library for multi-language MCP server development with production-grade patterns and best practices.*