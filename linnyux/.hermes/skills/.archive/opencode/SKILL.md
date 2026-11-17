---
name: opencode
description: "Delegate coding to OpenCode CLI (features, PR review)."
version: 1.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, OpenCode, Autonomous, Refactoring, Code-Review]
    related_skills: [claude-code, codex, hermes-agent]
---

# OpenCode CLI

<!--
  Linked references: references/google-gemini-models-v1.14.43.md, references/vertex-ai-service-account-auth.md, references/paperclip-opencode-adapter-setup.md, references/acpx-setup.md, references/gemini-litellm-opencode-limits.md
-->

Use [OpenCode](https://opencode.ai) as an autonomous coding worker orchestrated by Hermes terminal/process tools. OpenCode is a provider-agnostic, open-source AI coding agent with a TUI and CLI.

## When to Use

- User explicitly asks to use OpenCode
- You want an external coding agent to implement/refactor/review code
- You need long-running coding sessions with progress checks
- You want parallel task execution in isolated workdirs/worktrees

## Prerequisites

- OpenCode installed: `npm i -g opencode-ai@latest` or `brew install anomalyco/tap/opencode`
- Auth configured: `opencode auth login` or set provider env vars (OPENROUTER_API_KEY, etc.)
- Verify: `opencode auth list` should show at least one provider
- Git repository for code tasks (recommended)
- `pty=true` for interactive TUI sessions

## Provider Credentials (Critical)

OpenCode stores credentials in `~/.local/share/opencode/auth.json`. **Each provider has specific credential format requirements:**

### Google / Gemini
- The API key **MUST** be a proper Gemini API key from Google AI Studio (starts with `AIza...`)
- Google Cloud OAuth access tokens (starts with `AQ...`) will **NOT** work — OpenCode will hang silently on every request
- Verify the key format: `cat ~/.local/share/opencode/auth.json | python3 -c 'import sys,json; d=json.load(sys.stdin); print("google" in d, d.get("google",{}).get("key","")[:5])'`
- If the key starts with `AQ`, replace it with a real Gemini API key from https://aistudio.google.com/apikey
### Vertex AI — Use LiteLLM Proxy (Verified Working)

OpenCode's Google provider is hardcoded to the standard Gemini API and **cannot** use Vertex AI directly. However, the **LiteLLM proxy** workaround works reliably:

```
OpenCode → custom "vertex" provider in opencode.json → LiteLLM (port 4000) → Vertex AI
```

LiteLLM reads a GCP service account key, auto-refreshes OAuth tokens, and presents an OpenAI-compatible endpoint.

**When to use this:** The user has a GCP project with Vertex AI enabled and wants to use Gemini 3.1 models from OpenCode (or any OpenAI-compatible tool). They have a service account key or gcloud credentials.

**Full setup instructions** at `references/vertex-ai-service-account-auth.md` (section "WORKAROUND: LiteLLM Proxy").

Quick summary:
1. `pip3 install --break-system-packages 'litellm[proxy]'`
2. Create `~/litellm-config.yaml` with `vertex_ai/` model entries pointing at the service account key
3. `litellm --config ~/litellm-config.yaml --port 4000 --num_workers 1`
4. Add a `vertex` provider to `~/.config/opencode/opencode.json` pointing at `http://localhost:4000/v1`
5. Use `opencode run 'prompt' --model vertex/gemini-3.1-pro-preview`

**Critical region detail:** Vertex AI Gemini models use the **global** endpoint, not a regional one. `us-central1` returns 404 for many models. The LiteLLM config sets `vertex_location: global` to handle this.

### Direct Vertex AI API (Non-OpenCode)

### Groq (Free-Tier, No Credit Card)

Groq provides free-tier inference on open models via LPU hardware — no credit card needed to start. Add it as a provider in `~/.config/opencode/opencode.json`:

```json
{
  "groq": {
    "name": "Groq",
    "options": {
      "apiKey": "gsk_your_key_here",
      "baseURL": "https://api.groq.com/openai/v1"
    },
    "models": {
      "llama-3.3-70b-versatile": {"name": "Llama 3.3 70B"},
      "qwen/qwen3-32b": {"name": "Qwen 3 32B"},
      "meta-llama/llama-4-scout-17b-16e-instruct": {"name": "Llama 4 Scout"},
      "llama-3.1-8b-instant": {"name": "Llama 3.1 8B Instant"}
    }
  }
}
```

Use: `opencode run 'prompt' --model groq/llama-3.3-70b-versatile --print-logs 2>/dev/null`

To install on a remote machine over SSH, write the full `opencode.json` with `cat` heredoc or Python `json.dump()` (safe with JSON, unlike YAML).

### DeepSeek via LiteLLM (Alternative to Vertex AI)

If Vertex AI billing is disabled or you prefer DeepSeek models, add a DeepSeek provider to the same LiteLLM proxy. Full setup at `references/deepseek-provider-opencode.md`.

Quick summary:
1. Add a DeepSeek model entry to `~/litellm-config.yaml` (with `DEEPSEEK_API_KEY` or inline key)
2. Restart LiteLLM: `systemctl --user restart litellm-vertex.service`
3. Add `"deepseek"` provider block to `~/.config/opencode/opencode.json` (same `@ai-sdk/openai-compatible` pattern as the `vertex` provider)
4. Use: `opencode run 'prompt' --model deepseek/deepseek-v4-flash --print-logs 2>/dev/null`

Both Vertex AI and DeepSeek share the same LiteLLM proxy — no separate proxy needed.

For scripts and direct use, the Vertex AI endpoint format is:

```
POST https://aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/global/publishers/google/models/{MODEL}:generateContent
Authorization: Bearer $(gcloud auth print-access-token)
```

- The Google Cloud OAuth scope MUST be `cloud-platform` (NOT `generative-language`)
- The `generativelanguage.googleapis.com` endpoint requires a Gemini API key (AIza...) or generative-language scope, and needs billing enabled separately from Vertex AI

### Model Name Resolution
- Run `opencode models | grep <provider>` to see the **exact** model names available in OpenCode's catalog
- Do NOT guess the model name — OpenCode uses its own catalog, which may differ from the provider's API
- If a model isn't in the catalog, `opencode run` prints: `Error: Model not found: <model>. Did you mean: <alternatives>?`
- Example: `google/gemini-3.1-flash` does NOT exist in OpenCode; the correct names are `google/gemini-3.1-flash-lite`, `google/gemini-3.1-flash-image-preview`, `google/gemini-3.1-pro-preview`, etc.
- **IMPORTANT:** `opencode models` lists models from OpenCode's internal catalog, NOT what your credentials can actually access. A model may appear in the list but return 403/404 when used, if your API key lacks access or credits.

### Diagnosis When Models Hang or Fail
- **Wrong credentials cause silent hangs**, not quick errors. OpenCode waits for a timeout before surfacing the problem
- Always wrap first-run tests with `timeout 30`: `timeout 30 opencode run 'test' --model <provider/model>`
- If the command hangs >30s, check credentials first, then model name
- If the command errors quickly with `ProviderModelNotFoundError` or a model-not-found, use `opencode models | grep <provider>` to find the exact name — the model doesn't exist in OpenCode's catalog

## Binary Resolution (Important)

Shell environments may resolve different OpenCode binaries. If behavior differs between your terminal and Hermes, check:

```
terminal(command="which -a opencode")
terminal(command="opencode --version")
```

If needed, pin an explicit binary path:

```
terminal(command="$HOME/.opencode/bin/opencode run '...'", workdir="~/project", pty=true)
```

## One-Shot Tasks

Use `opencode run` for bounded, non-interactive tasks.

**Critical: `--print-logs` required in Hermes terminal sessions.** When invoked from Hermes's terminal tool (no real TTY), `opencode run` without `--print-logs` just prints help text and exits 1. The `--print-logs` flag forces the command to actually execute. Always pipe stderr to /dev/null to suppress verbose log noise:

```bash
opencode run 'prompt' --model provider/model --print-logs 2>/dev/null
```

Without `2>/dev/null`, the logs intermix with output. With it, only the model's response text appears on stdout.

The `--command` flag accepts a string positional instead of using the message array. Example:
```bash
opencode run --command 'Refactor the auth module' --model vertex/gemini-2.5-flash --print-logs 2>/dev/null
```

```
terminal(command="opencode run 'Add retry logic to API calls and update tests'", workdir="~/project")
```

Attach context files with `-f`:

```
terminal(command="opencode run 'Review this config for security issues' -f config.yaml -f .env.example --print-logs 2>/dev/null", workdir="~/project")
```

Show model thinking with `--thinking`:

```
terminal(command="opencode run 'Debug why tests fail in CI' --thinking --print-logs 2>/dev/null", workdir="~/project")
```

Force a specific model:

```
terminal(command="opencode run 'Refactor auth module' --model openrouter/anthropic/claude-sonnet-4 --print-logs 2>/dev/null", workdir="~/project")
```

## Interactive Sessions (Background)

For iterative work requiring multiple exchanges, start the TUI in background:

```
terminal(command="opencode", workdir="~/project", background=true, pty=true)
# Returns session_id

# Send a prompt
process(action="submit", session_id="<id>", data="Implement OAuth refresh flow and add tests")

# Monitor progress
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")

# Send follow-up input
process(action="submit", session_id="<id>", data="Now add error handling for token expiry")

# Exit cleanly — Ctrl+C
process(action="write", session_id="<id>", data="\x03")
# Or just kill the process
process(action="kill", session_id="<id>")
```

**Important:** Do NOT use `/exit` — it is not a valid OpenCode command and will open an agent selector dialog instead. Use Ctrl+C (`\x03`) or `process(action="kill")` to exit.

### TUI Keybindings

| Key | Action |
|-----|--------|
| `Enter` | Submit message (press twice if needed) |
| `Tab` | Switch between agents (build/plan) |
| `Ctrl+P` | Open command palette |
| `Ctrl+X L` | Switch session |
| `Ctrl+X M` | Switch model |
| `Ctrl+X N` | New session |
| `Ctrl+X E` | Open editor |
| `Ctrl+C` | Exit OpenCode |

### Resuming Sessions

After exiting, OpenCode prints a session ID. Resume with:

```
terminal(command="opencode -c", workdir="~/project", background=true, pty=true)  # Continue last session
terminal(command="opencode -s ses_abc123", workdir="~/project", background=true, pty=true)  # Specific session
```

## Common Flags

| Flag | Use |
|------|-----|
| `run 'prompt'` | One-shot execution and exit |
| `--continue` / `-c` | Continue the last OpenCode session |
| `--session <id>` / `-s` | Continue a specific session |
| `--agent <name>` | Choose OpenCode agent (build or plan) |
| `--model provider/model` | Force specific model |
| `--format json` | Machine-readable output/events |
| `--file <path>` / `-f` | Attach file(s) to the message |
| `--thinking` | Show model thinking blocks |
| `--variant <level>` | Reasoning effort (high, max, minimal) |
| `--title <name>` | Name the session |
| `--attach <url>` | Connect to a running opencode server |

## Procedure

1. Verify tool readiness:
   - `terminal(command="opencode --version")`
   - `terminal(command="opencode auth list")`
2. For one-shot tasks, use `opencode run 'prompt' --model provider/model --print-logs 2>/dev/null` (the `--print-logs` flag is mandatory in Hermes terminal sessions — without it the command prints help and exits 1). No pty needed.
3. For iterative tasks, start `opencode` with `background=true, pty=true`.
4. Monitor long tasks with `process(action="poll"|"log")`.
5. If OpenCode asks for input, respond via `process(action="submit", ...)`.
6. Exit with `process(action="write", data="\x03")` or `process(action="kill")`.
7. Summarize file changes, test results, and next steps back to user.

## PR Review Workflow

OpenCode has a built-in PR command:

```
terminal(command="opencode pr 42", workdir="~/project", pty=true)
```

Or review in a temporary clone for isolation:

```
terminal(command="REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && opencode run 'Review this PR vs main. Report bugs, security risks, test gaps, and style issues.' -f $(git diff origin/main --name-only | head -20 | tr '\n' ' ')", pty=true)
```

## Parallel Work Pattern

Use separate workdirs/worktrees to avoid collisions:

```
terminal(command="opencode run 'Fix issue #101 and commit'", workdir="/tmp/issue-101", background=true, pty=true)
terminal(command="opencode run 'Add parser regression tests and commit'", workdir="/tmp/issue-102", background=true, pty=true)
process(action="list")
```

## Session & Cost Management

List past sessions:

```
terminal(command="opencode session list")
```

Check token usage and costs:

```
terminal(command="opencode stats")
terminal(command="opencode stats --days 7 --models anthropic/claude-sonnet-4")
```

## Pitfalls

- Interactive `opencode` (TUI) sessions require `pty=true`. The `opencode run` command does NOT need pty.
- **`opencode run` shows help instead of executing** in Hermes terminal sessions — always add `--print-logs 2>/dev/null`. Without `--print-logs`, the `run` subcommand outputs its own help text and exits with code 1 instead of running the prompt. This is an OpenCode v1.4.3 behavior quirk in non-TTY environments.
- `/exit` is NOT a valid command — it opens an agent selector. Use Ctrl+C to exit the TUI.
- PATH mismatch can select the wrong OpenCode binary/model config.
- If OpenCode appears stuck, inspect logs before killing:
  - `process(action="log", session_id="<id>")`
- Avoid sharing one working directory across parallel OpenCode sessions.
- Enter may need to be pressed twice to submit in the TUI (once to finalize text, once to send).
- **Hermes credential pool masks API keys.** Keys stored in `~/.hermes/.env` or the credential pool (`~/.hermes/auth.json`) have their middles replaced with `...`. Pasting a masked key into `opencode.json`'s `apiKey` field will fail at DeepSeek/OpenAI/any direct API call with `401 Authentication Fails`. Always paste a raw unmasked key directly into `opencode.json`, or use a LiteLLM proxy so the key never leaves the proxy's env.


### Provider Catalog vs. Credential Access
- The `opencode` binary contains a hardcoded `snapshot3` object (a "model catalog").
- **UI Detection:** Any TUI or UI component (like the Paperclip board) that queries this catalog will display all providers/models (e.g., DeepSeek, MiniMax) as available.
- **Truth:** Appearance in this catalog does **not** indicate your credentials have access.
- **Troubleshooting:** If you see "DeepSeek" or other unexpected providers, ignore them. As long as you have configured your adapter (e.g., LiteLLM proxy for Vertex AI) in your `opencode.json` (for local use) or via Paperclip adapter settings, the agent will use your explicitly configured provider/model.


## Verification

Smoke test (must include `--print-logs` and `2>/dev/null` in non-TTY contexts):

```
terminal(command="opencode run 'Respond with exactly: OPENCODE_SMOKE_OK' --print-logs 2>/dev/null")
```

Success criteria:
- Output includes `OPENCODE_SMOKE_OK`
- Command exits without provider/model errors
- For code tasks: expected files changed and tests pass

Common failure modes:
- **Shows help text instead of running** — forgot `--print-logs`. Add it.
- **Exit code 1, empty output** — either missing `--print-logs`, or model name not in OpenCode's catalog. Run `opencode models | grep <provider>` to verify the exact name.
- **Hangs for >30s** — wrong credentials or model name. Use `timeout 30` for first-run tests.
- **`--dangerously-skip-permissions` not supported** — the `run` subcommand does not accept this flag. It only applies to interactive/TUI sessions.

## Rules

1. Prefer `opencode run` for one-shot automation — it's simpler and doesn't need pty.
2. Use interactive background mode only when iteration is needed.
3. Always scope OpenCode sessions to a single repo/workdir.
4. For long tasks, provide progress updates from `process` logs.
5. Report concrete outcomes (files changed, tests, remaining risks).
6. Exit interactive sessions with Ctrl+C or kill, never `/exit`.
