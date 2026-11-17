# VS Code / Windsurf / Antigravity Extension Pattern

When you need to distribute an MCP server as a **proper IDE extension** (not
just an MCP config file), create a VS Code extension package. It works in
VS Code, Windsurf (Codeium fork), and Antigravity (Gemini fork) — all three
support VS Code extension `.vsix` files.

## When to Use This Instead of MCP Config

| Use case | Approach |
|----------|----------|
| User just needs the MCP tools available in the IDE agent | MCP config JSON file |
| User needs a dashboard, status bar, commands, auto-sync, or configuration UI | **VS Code extension** |
| You want to distribute via VS Code Marketplace / Open VSX | VS Code extension |
| You want auto-configuration on install | VS Code extension |

## Package Structure

```
ides/extension/
├── package.json              ← VS Code extension manifest
├── tsconfig.json
├── src/
│   └── extension.ts          ← Activation entry point
└── node_modules/
```

## package.json — VS Code Manifest

Minimal but complete:

```json
{
  "name": "synapse-memory",
  "displayName": "Synapse Memory",
  "description": "Persistent AI memory backbone — store/retrieve project knowledge.",
  "version": "0.1.0",
  "publisher": "your-org",
  "engines": { "vscode": "^1.85.0" },
  "categories": ["Programming Languages", "Machine Learning", "Other"],
  "activationEvents": ["onStartupFinished"],
  "main": "./dist/extension.js",
  "contributes": {
    "commands": [
      { "command": "synapse.store", "title": "Synapse: Store Memory" },
      { "command": "synapse.retrieve", "title": "Synapse: Retrieve Memories" },
      { "command": "synapse.health", "title": "Synapse: Check Server Status" },
      { "command": "synapse.context", "title": "Synapse: Get Context Pack" },
      { "command": "synapse.configure", "title": "Synapse: Configure Server" },
      { "command": "synapse.openDashboard", "title": "Synapse: Open Dashboard" }
    ],
    "viewsContainers": {
      "activitybar": [{
        "id": "synapse-sidebar",
        "title": "Synapse Memory",
        "icon": "$(database)"
      }]
    },
    "views": {
      "synapse-sidebar": [
        { "id": "synapse.overview", "name": "Memory Overview" },
        { "id": "synapse.quickStore", "name": "Quick Store" }
      ]
    },
    "configuration": {
      "title": "Synapse Memory",
      "properties": {
        "synapse.serverUrl": {
          "type": "string",
          "default": "http://localhost:8765/mcp"
        },
        "synapse.apiKey": {
          "type": "string",
          "default": ""
        },
        "synapse.defaultProject": {
          "type": "string",
          "default": "default"
        },
        "synapse.autoSync": {
          "type": "boolean",
          "default": true
        }
      }
    }
  },
  "scripts": {
    "compile": "tsc -p ./tsconfig.json",
    "package": "vsce package",
    "package:ovsx": "npx ovsx package"
  },
  "devDependencies": {
    "@types/vscode": "^1.85.0",
    "@types/node": "*",
    "typescript": "^5.0.0",
    "vsce": "^2.0.0"
  }
}
```

## extension.ts — Activation Pattern

### 1. Host Detection

Detect which IDE the extension runs in using `vscode.env.appName`:

```typescript
const HOST_ADAPTERS = [
  { id: "vscode", label: "VS Code",
    detect: (app) => !app.includes("windsurf") && !app.includes("antigravity"),
    configPath: path.join(os.homedir(), ".vscode", "mcp.json"),
    configKey: "servers" },
  { id: "windsurf", label: "Windsurf",
    detect: (app) => app.includes("windsurf") || app.includes("codeium"),
    configPath: path.join(os.homedir(), ".codeium", "windsurf", "mcp_config.json"),
    configKey: "mcpServers" },
  { id: "antigravity", label: "Antigravity",
    detect: (app) => app.includes("antigravity") || app.includes("gemini"),
    configPath: path.join(os.homedir(), ".gemini", "antigravity", "mcp_config.json"),
    configKey: "mcpServers" },
];

function detectHost() {
  const appName = vscode.env.appName ?? "";
  return HOST_ADAPTERS.find(a => a.detect(appName)) ?? null;
}
```

### 2. MCP Config Writer

On activation, write the MCP config so the IDE's built-in agent can also
use the server directly:

```typescript
function writeMCPConfig(host): boolean {
  const dir = path.dirname(host.configPath);
  fs.mkdirSync(dir, { recursive: true });
  let config = fs.existsSync(host.configPath)
    ? JSON.parse(fs.readFileSync(host.configPath, "utf-8"))
    : {};
  const servers = config[host.configKey] ?? {};
  if (!servers["synapse"]) {
    servers["synapse"] = {
      url: "http://100.91.55.113:8765/mcp",
      timeout: 120, connect_timeout: 30,
    };
    config[host.configKey] = servers;
    fs.writeFileSync(host.configPath, JSON.stringify(config, null, 2));
    return true;
  }
  return false;
}
```

### 3. MCP Client (Session Cache)

Avoid per-call session init. Cache one session per process:

```typescript
let _session: { id: string; expiresAt: number } | null = null;

async function ensureSession(url: string): Promise<string> {
  const now = Date.now();
  if (_session && now < _session.expiresAt) return _session.id;
  const resp = await fetch(url, { method: "POST", headers: {...},
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "initialize", ... }) });
  const id = resp.headers.get("mcp-session-id") ?? "";
  if (!id) throw new Error("No MCP session");
  _session = { id, expiresAt: now + 840_000 };
  return id;
}
```

### 4. Status Bar

Show connection state at a glance:

```typescript
let _statusBarItem: vscode.StatusBarItem | null = null;

function updateStatusBar(connected: boolean) {
  if (!_statusBarItem) return;
  _statusBarItem.text = connected ? "$(database) Synapse" : "$(circle-slash) Synapse";
  _statusBarItem.tooltip = connected ? "Connected" : "Disconnected (click to configure)";
  _statusBarItem.backgroundColor = connected ? undefined
    : new vscode.ThemeColor("statusBarItem.warningBackground");
  _statusBarItem.show();
}
```

### 5. Commands

Each command calls the MCP server, formats the result, and presents it:

- **commandHealth()**: Calls `health` tool, shows stats in info message, updates status bar
- **commandStore()**: Prompts for content/kind/importance via `showInputBox` + `showQuickPick`, calls `store`
- **commandRetrieve()**: Prompts for query, calls `retrieve`, displays results in a `WebviewPanel`
- **commandContext()**: Prompts for task description, calls `context`, shows token savings
- **commandConfigure()**: Prompts for server URL, updates config

### 6. File Save Auto-Sync

Optionally store working-memory entries on file save:

```typescript
vscode.workspace.onDidSaveTextDocument(async (doc) => {
  if (doc.uri.scheme !== "file") return;
  await callServer(getServerUrl(), "store", {
    project_key: getConfig("defaultProject", "default"),
    kind: "working",
    content: `Edited: ${path.basename(doc.uri.fsPath)}`,
    importance: 0.3,
  });
});
```

### 7. Results Display (Webview)

For search results, use a webview panel for rich display:

```typescript
const panel = vscode.window.createWebviewPanel(
  "synapseResults", `Synapse: "${query}"`,
  vscode.ViewColumn.Two, { enableScripts: false }
);
panel.webview.html = `<html><body>${formattedResults}</body></html>`;
```

## Building & Packaging

```bash
cd ides/extension
npm install
npm run compile          # → dist/extension.js
npm run package          # → synapse-memory-0.1.0.vsix
```

Install in any supported IDE:
```bash
# VS Code
code --install-extension synapse-memory-0.1.0.vsix

# Windsurf (has its own CLI)
windsurf --install-extension synapse-memory-0.1.0.vsix

# Antigravity (has its own CLI)
antigravity --install-extension synapse-memory-0.1.0.vsix
```

## Pitfalls

- **Module resolution**: `vscode` module is only available inside the extension host. Use `@types/vscode` for type checking, and `@types/node` for Node built-ins (fs, path, os).
- **`fetch` in VS Code**: VS Code's extension host supports `fetch()` natively (it's polyfilled by Electron). No need for `node-fetch` or `axios`.
- **Target library**: Add `"lib": ["ES2022"]` to tsconfig — `fetch` is in ES2022 global scope. Do NOT add `"dom"` (it brings in browser types that conflict with VS Code types).
- **Webview security**: Set `enableScripts: false` when displaying untrusted content. Use `escapeHtml()` on any user-provided text rendered in the webview.
- **Command interference**: Prefixed command IDs (`synapse.*`) avoid conflicts. The status bar command should call a user-facing dashboard command, not an internal-only function.
- **Auto-sync noise**: Only trigger on `scheme === "file"` to skip virtual documents. Set low importance (0.3) so working-memory writes don't pollute semantic memory.
- **Extension takes time to activate**: VS Code extensions with `onStartupFinished` may take 5-10 seconds to activate after window load. Handle async initialization gracefully — don't rely on extension being ready for the first file save event.
