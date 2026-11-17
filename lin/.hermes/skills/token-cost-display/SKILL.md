---
name: token-cost-display
description: Show estimated token usage and cost with each message. Enables Hermes' built-in show_cost config, appends a usage/cost summary footer to every agent response, and provides a hermes insights dashboard for deeper session analytics.
metadata:
  openclaw:
    emoji: 💰
    requires:
      bins: [hermes]
---

# Token & Cost Display

## Overview

Appends a compact token/cost summary to every assistant response so you always know what each message costs. Also enables Hermes' built-in `show_cost` bar and exposes `hermes insights` for deeper dives.

There are three layers:

---

## 1. Built-in: `display.show_cost`

Hermes has a config toggle that shows estimated cost in the CLI status bar.

```bash
hermes config set display.show_cost true
```

This adds a cost readout to the bottom of the CLI/TUI interface. To verify:

```bash
hermes config get display.show_cost
```

The status bar shows the model used and running cost estimate for the session.

---

## 2. Agent-footer: per-message summary

When this skill is loaded, the agent appends a usage summary footer to each response:

```
── Usage ────────────────────────────────────
Model: deepseek/deepseek-v4-flash
Session messages: N | ~X,XXX tokens
Provider: openrouter
─────────────────────────────────────────────
```

The agent reads current message count and token estimates from session metadata.

---

## 3. Dashboard: `hermes insights`

For full session analytics:

```bash
hermes insights
```

This shows:
- Per-session token usage
- Per-model cost breakdowns
- Activity timelines
- Cumulative spending

---

## Configuration

### Enable persistent cost display

```bash
hermes config set display.show_cost true
```

### Enable the runtime footer (optional -- shows model, context %, cwd in CLI)

```bash
hermes config set display.runtime_footer.enabled true
```

### Check current cost display status

```bash
hermes config get display.show_cost
```

---

## Usage / Trigger

This skill is triggered automatically when loaded. The agent appends the usage footer at the end of each response.

To enable permanently, add it to your preloaded skills in config.yaml:

```yaml
# In ~/.hermes/config.yaml, under skills:
preload: [token-cost-display]
```

Or load on-demand per session:

```bash
hermes chat -s token-cost-display
```

---

## Pitfalls

- Token counts are **estimates** (approximate from session message count and model context usage). Actual OpenRouter billing may differ slightly.
- `display.show_cost` only works in CLI/TUI mode -- not in Telegram, Discord, or other platforms.
- Running `hermes insights` creates a separate subprocess and may take a moment.
- Cost estimates depend on OpenRouter's per-model pricing being up to date.
- The footer is appended by the agent itself -- it is advisory, not a precise billing record.
- **This skill is REDUNDANT if `display.show_cost: true` is already set in config.yaml** — the built-in config already shows cost in the status bar. Loading this skill adds its full SKILL.md (~3KB) to every system prompt for no additional benefit. Prefer the config toggle over this skill. Remove from `skills.preload` if `show_cost` is already on.
