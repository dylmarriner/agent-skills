# acpx — ACP CLI Client Setup

Installed from source on kubuntux: `github.com/openclaw/acpx` v0.7.0.

## Installation (from source)

```bash
git clone https://github.com/openclaw/acpx.git ~/acpx
cd ~/acpx
pnpm install
pnpm approve-builds    # accept esbuild
pnpm build
npm install -g .        # links into PATH
```

Alternatively: `npm install -g acpx` if you just want the npm package.

## Usage with OpenCode + Vertex AI / LiteLLM

acpx connects to ACP-compatible coding agents. OpenCode supports ACP natively:

```bash
# One-shot via OpenCode (which uses LiteLLM -> Vertex AI)
acpx opencode exec 'your prompt' --model vertex/gemini-3.1-pro-preview

# Interactive session
acpx opencode 'your prompt'
```

The `--model` flag is passed through to OpenCode, which resolves it against its provider config. With the `vertex` provider configured in `opencode.json`, use `vertex/gemini-3.1-pro-preview`.

## Built-in Agent Registry

acpx resolves agent names to commands via `src/agent-registry.ts`:

| Name | Command |
|------|---------|
| `pi` | `npx pi-acp` |
| `openclaw` | `openclaw acp` |
| `codex` | `npx @zed-industries/codex-acp` |
| `claude` | `npx -y @agentclientprotocol/claude-agent-acp` |
| `gemini` | `gemini --acp` |
| `opencode` | `npx -y opencode-ai acp` |
| `cursor` | `cursor-agent acp` |
| `copilot` | `copilot --acp --stdio` |
| `droid` | `droid exec --output-format acp` |

## Custom Agent Command

Use `--agent` for arbitrary ACP-compatible commands:

```bash
acpx --agent './my-custom-acp-server' 'your prompt'
```
