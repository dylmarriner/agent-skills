# DeepSweep — Review My AI Agent Environment

[![Version](https://img.shields.io/visual-studio-marketplace/v/deepsweep-ai.deepsweep?style=flat&labelColor=0D1B2A&color=06B6D4)](https://marketplace.visualstudio.com/items?itemName=deepsweep-ai.deepsweep)
[![Installs](https://img.shields.io/visual-studio-marketplace/i/deepsweep-ai.deepsweep?style=flat&labelColor=0D1B2A&color=06B6D4)](https://marketplace.visualstudio.com/items?itemName=deepsweep-ai.deepsweep)
[![Patterns](https://img.shields.io/badge/patterns-77-0D1B2A?style=flat&labelColor=0D1B2A&color=06B6D4)](https://marketplace.visualstudio.com/items?itemName=deepsweep-ai.deepsweep)
[![AI-specific](https://img.shields.io/badge/AI--specific-37-0D1B2A?style=flat&labelColor=0D1B2A&color=F5C518)](https://marketplace.visualstudio.com/items?itemName=deepsweep-ai.deepsweep)
[![Runs locally](https://img.shields.io/badge/runs-locally-0D1B2A?style=flat&labelColor=0D1B2A&color=10B981)](https://marketplace.visualstudio.com/items?itemName=deepsweep-ai.deepsweep)

**Run one command — `DeepSweep: Review My Agent Environment` — and see exactly what your AI coding agent can do in this workspace, where it can act beyond what it should, and how to close the gap. Local, metadata-only, no account, no cloud.**

DeepSweep reviews your AI agent's environment and continuously checks AI-generated code for the things assistants consistently get wrong — locally, in real time, before it lands in your repo. Works with Cursor, GitHub Copilot, Claude Code, Windsurf, and any AI coding tool. 77 patterns. Sub-second. Zero configuration.

---

## Review My Agent Environment

AI coding agents quietly accumulate capabilities you never explicitly granted — MCP servers with broad tool access, shell execution, database reach, repository write, deploy hooks. **`DeepSweep: Review My Agent Environment`** maps them in a single local pass:

- **[CAPABILITIES]** Detects what the agent can actually do — MCP tool access, shell execution, database access, repository write, deploy — by reading your workspace config (`.cursorrules`, `mcp.json`, agent settings). Metadata only; no source ever leaves the editor.
- **[IDENTITY]** Derives a deterministic local agent identity, so the review is stable and reproducible from one run to the next.
- **[GAPS]** Evaluates an advisory authorization policy and surfaces every gap where the agent can act beyond what it should — as findings you can read and act on, not enforcement that blocks you.

Runs fully on-device in under a second. **No account, no cloud, no upload. Free.**

---

## Catch what AI assistants miss, as you type

Beyond the one-time environment review, DeepSweep watches every change your AI assistant makes and flags risk the moment it lands.

Traditional SAST tools (Snyk, SonarQube, Semgrep) check hand-written code against hand-written rules. They were not designed for the verification gap that opens every time an AI agent generates, pastes, or modifies code in your editor.

DeepSweep is the **first runtime-aware security tool built for agentic code**. It detects the things AI assistants consistently get wrong — prompt injection in rules files, hallucinated dependencies, hardcoded secrets pasted from example code, MCP tool-access misconfigurations, and Unicode backdoors that look invisible to humans but execute faithfully at runtime.

- **[VERIFY]** Checks every save and keystroke (800 ms debounce). No CI wait.
- **[LOCAL]** Pattern matching runs entirely on your machine. Source never leaves the editor.
- **[AGENTIC]** AI-specific patterns with CVE references. Built for the `.cursorrules`, `mcp.json`, and agent-config attack surface.

---

## Quick Start

1. **Install** — search `DeepSweep` in the Extensions view and click **Install**.
2. **Review your agent** — run `DeepSweep: Review My Agent Environment` from the Command Palette to see your agent's capabilities and authorization gaps.
3. **Open a project** — DeepSweep then checks AI-generated code automatically on open and on save.
4. **Fix findings** — click any finding for a one-line fix hint, or copy a remediation prompt and paste it back to your AI assistant.

Keyboard: `Cmd+Shift+S` (macOS) / `Ctrl+Shift+S` (Windows/Linux) to check the current file.

---

## What It Detects

| Category | Examples | Severity |
|----------|----------|----------|
| **Agent Authorization Gaps** | Agent can reach MCP tools, shell, database, repo write, or deploy beyond its intended scope | High |
| **Rules File Backdoors** | Invisible Unicode, bidirectional text overrides, hidden instructions in `.cursorrules` | Critical |
| **Prompt Injection** | Instruction override, role reassignment in agent-config files | Critical |
| **Credential Exposure** | Hardcoded API keys, AWS secrets, Stripe keys, private keys | Critical |
| **Data Exfiltration** | Code or secrets routed to external URLs via rules files | Critical |
| **MCP Security** | Unrestricted tool access, remote server connections, missing sandboxing | High |
| **Supply Chain** | Hallucinated packages, typosquatted dependencies, slopsquatting | High |
| **Injection Flaws** | SQL injection, XSS, command injection, path traversal | High |
| **Misconfigurations** | Insecure crypto, disabled TLS verification, debug mode in production | Medium |

**77 patterns total** — 37 AI-specific and agentic-code-aware (prompt injection, MCP, rules-file, exfiltration, config) plus 40 traditional security patterns.

---

## Features

- **Review My Agent Environment** — one-command local review of your agent's capabilities, identity, and authorization gaps (no account, no cloud)
- **Live Checks** — analyzes AI-generated code as you type, with an 800 ms debounce
- **Certify-on-Write** — catches an AI agent the moment it writes a new critical/high finding, with one-click Revert / Auto-Fix
- **Verification Proof** — see exactly what was checked: patterns, files, categories, duration
- **9 UI Surfaces** — status bar, Problems panel, CodeLens, Quick Fix, tree view, webview, decorations, notifications, output channel
- **AI Assistant Detection** — identifies which tool generated the code (Cursor, Copilot, Claude, Windsurf)
- **Finding Suppression** — suppress with reason categories, expiration dates, and audit trails
- **Fix All Auto-Correct** — one-click static fixes across your workspace
- **Security Badge** — copy a shields.io-style badge for your README
- **Config File Monitoring** — auto-rechecks when `.cursorrules`, `.env`, or `mcp.json` change

---

## Pricing

| | Free | Pro | Team |
|---|---|---|---|
| **Agent Environment Review** | Yes | Yes | Yes |
| **Code checks** | Unlimited | Unlimited | Unlimited |
| **Patterns** | 77 | 77 | 77 |
| **Fix hints** | Yes | Yes | Yes |
| **Full fix prompts** | — | Yes | Yes |
| **Finding suppression** | Session only | Persistent | Persistent + audit trail |
| **Security badge** | — | Yes | Yes |
| **Fix All auto-correct** | — | Yes | Yes |
| **Price** | $0 | $19/mo | $99/mo |

The Repo Grade, the AI Code Health Score, and the Agent Environment Review are free forever. Paid tiers unlock the fixes, never the grade. All checks run locally — no code is sent to external servers for pattern matching.

---

## About: Behavioral Output Certification

Traditional AI safety is an alignment problem — train the model to want the right thing. But alignment is a statistical promise, not a per-output proof. An aligned coding agent can still silently delete a permission check, paste a hardcoded credential, or generate a `.cursorrules` file that hides instructions in invisible Unicode.

**Behavioral Output Certification (BOC)** is the runtime layer that closes this gap. For every AI-generated change, DeepSweep issues a certificate: *what the agent was asked to do, what it actually did, and the quantified gap between the two*. The certificate is the artifact. The artifact is the audit trail. The audit trail is what turns alignment into accountability.

This extension is the reference implementation. The full argument lives in the book:

> **[The Verification Gap — AI Safety Beyond Alignment: Why Outputs Must Be Certified](https://www.amazon.com/dp/B0GWV9FGDF)**
> Book One in the DeepSweep.ai Thesis series, by Brad McEvilly.

---

## Coming Soon: Agent Interoperability Bridge

DeepSweep is building the **security layer for the AI agent protocol stack**.

- **A2A Agent Card Review** — 10 new security patterns for Google's Agent-to-Agent protocol
- **ACP Manifest Checks** — 5 new patterns for IBM's Agent Communication Protocol
- **Cross-Protocol Security Graph** — map dependencies between MCP, A2A, and ACP configs in your workspace
- **Transitive Risk Analysis** — when an MCP server is flagged, see which A2A workflows are affected

Phase 1 (A2A review) and Phase 2 (cross-protocol graph) are in development. 15 new patterns total (`DS-A2A-001..010`, `DS-ACP-001..005`).

---

## Requirements

- VS Code 1.74.0+, Cursor, or Windsurf
- Node.js runtime (included with VS Code)

---

## Commands

| Command | Description |
|---------|-------------|
| `DeepSweep: Review My Agent Environment` | Review your AI agent's capabilities, identity, and authorization gaps |
| `DeepSweep: Validate Project` | Check the entire workspace |
| `DeepSweep: Validate Current File` | Check the active file |
| `DeepSweep: Copy Fix Prompt` | Copy remediation prompt for your AI assistant |
| `DeepSweep: Fix All (Auto-Correct)` | Apply all static fixes |
| `DeepSweep: Copy Security Badge` | Copy badge markdown for your README |
| `DeepSweep: Sign In with GitHub` | Unlock paid features |

---

## Privacy

DeepSweep runs pattern matching and the agent-environment review **locally in your editor**. No source code is sent to external servers for analysis. Anonymous usage telemetry helps improve detection accuracy and can be disabled in settings.

[Privacy Policy](https://deepsweep.ai/privacy)

---

## Links

- [Website](https://deepsweep.ai)
- [The Verification Gap (book)](https://www.amazon.com/dp/B0GWV9FGDF)
- [Changelog](https://github.com/deepsweep-ai/deepsweep-vscode/blob/main/CHANGELOG.md)
- [Report Issues](https://github.com/deepsweep-ai/deepsweep-vscode/issues)
- [Open VSX](https://open-vsx.org/extension/deepsweep-ai/deepsweep)
