# Kāwana VS Code Extension

Enterprise AI governance dashboard — hooks, skills, presets, and MCP control plane.

## Features

- **Activity Bar Dashboard** — Six panels: Overview, Dashboard, Hooks, Skills, Diagnostics, Governance
- **Host-Aware** — Auto-detects VS Code, Windsurf, or Antigravity and writes MCP config correctly
- **Asset Management** — Toggle hooks/skills on/off without reinstalling
- **Presets** — One-click governance mode (free/balanced/strict/paranoid/enterprise)
- **License Management** — Free/Pro/Enterprise tier enforcement
- **Integrations** — Broker health, diagnostics, repair, rollback

## Installation

### Prerequisites

- VS Code 1.85.0+
- Node.js 18+

### Install Steps

1. Clone this repository
2. Install dependencies:
   ```
   cd packages/extension && npm install
   ```
3. Compile TypeScript:
   ```
   npm run compile
   ```
4. Package the extension:
   ```
   npm run package
   ```
5. Install the resulting `.vsix` file in VS Code: `code --install-extension kawana-extension-1.0.0.vsix`

### Alternative: Development Mode

Run the extension in debug mode:
```
# Press F5 in VS Code with the extension project open
# Or from command palette: "Debug: Start Debugging"
```

## Commands

All commands are prefixed with `kawana.`:

| Command | Description |
|---------|-------------|
| `kawana.setup` | First-time setup wizard |
| `kawana.installBroker` | Install the broker binary |
| `kawana.installAssets` | Deploy hooks/skills |
| `kawana.enableAsset` | Enable a hook or skill |
| `kawana.disableAsset` | Disable a hook or skill |
| `kawana.applyPreset` | Apply a governance preset |
| `kawana.refreshHealth` | Refresh broker health status |
| `kawana.repair` | Repair broken assets (Pro tier) |
| `kawana.rollback` | Rollback to previous state (Pro tier) |
| `kawana.activateLicense` | Activate license key |
| `kawana.openLogs` | Open extension logs |
| `kawana.openDashboard` | Focus the dashboard panel |

## Views

The extension contributes a **Kāwana** container to the Activity Bar with these views:

| View ID | Type | Description |
|---------|------|-------------|
| `kawana.overview` | Tree | Broker status, host, tier summary |
| `kawana.dashboard` | Webview | Rich HTML dashboard with quick actions |
| `kawana.hooks` | Tree | All hooks grouped by provider |
| `kawana.skills` | Tree | All skills grouped by provider |
| `kawana.diagnostics` | Tree | Health, errors, repair actions |
| `kawana.governance` | Tree | Governance mode, presets, policy status |
| `kawana.license` | Tree | Tier, features, activation |

## Host Detection

The extension auto-detects the IDE and configures MCP accordingly:

| Host | Detected by | Config Path | Schema |
|------|------------|--------------|--------|
| VS Code | appName not windsurf/antigravity | `.vscode/mcp.json` | `servers` |
| Windsurf | appName contains "windsurf"/"codeium" | `~/.codeium/windsurf/mcp_config.json` | `mcpServers` |
| Antigravity | appName contains "antigravity"/"gemini" | `~/.gemini/antigravity/mcp_config.json` | `mcpServers` |

## Entitlements

| Tier | Features |
|------|----------|
| Free | Core governance, basic hooks, dashboard, diagnostics |
| Pro | Full hook packs, advanced presets, repair/rollback, kill switch |
| Enterprise | Policy locking, signed bundles, audit export, org templates |

License activation: `kawana.activateLicense` with key format:
- `--PRO--xxxx` → Pro tier
- `--ENT--xxxx` → Enterprise tier

## Configuration

Settings under `kawana.` namespace:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `brokerPath` | string | auto | Path to broker binary |
| `installerPath` | string | auto | Path to installer binary |
| `defaultScope` | workspace|user | workspace | MCP install scope |
| `autoStartBroker` | boolean | true | Auto-verify broker on activate |
| `logLevel` | info | info | Log verbosity |

## Troubleshooting

### Extension not appearing

- Ensure VS Code 1.85.0+
- Check Output panel for errors: `View > Output > Select "Kāwana"`
- Try reloading window: `Developer: Reload Window`

### Broker not starting

- Verify broker binary exists
- Check logs: `kawana.openLogs`
- Run installer doctor: `kawana.repair`

### MCP server not registered

- Run setup wizard: `kawana.setup`
- Manually check config file exists in expected location

## Building

```
# Install deps
npm install

# Compile TypeScript
npm run compile

# Run tests
npm test

# Package for marketplace
npm run package

# Also available for Open VSX (Windsurf distribution)
npm run package:ovsx
```

## Architecture

```
packages/extension/
├── src/
│   ├── extension.ts      — Activation entry, service wiring
│   ├── commands/         — kawana.* command handlers
│   ├── services/         — Business logic (Host, Broker, Asset, License)
│   ├── host-adapters/    — IDE--specific config writers
│   ├── views/           — Tree view data providers
│   ├── webview/         — Dashboard webview
│   └── models/         — TypeScript types
└── package.json       — VS Code extension manifest
```

## License

MIT
