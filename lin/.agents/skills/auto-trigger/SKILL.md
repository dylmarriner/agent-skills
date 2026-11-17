---
name: auto-trigger
description: Workflow automation hooks for agent-playbook skills. This skill defines automatic triggers between skills - DO NOT use directly, it's a configuration skill that other skills reference.
allowed-tools: Read, Write, Edit
hooks: []
---

# Auto-Trigger Hooks

**Configuration Reference for Workflow Automation**

This skill defines the hook format that other skills use to automatically trigger follow-up actions. When a skill completes its workflow, it can automatically trigger other skills based on the hooks defined in its `metadata.hooks` section.

## Current Implementation Status

| Skill | Hook Type | Triggers |
|-------|-----------|----------|
| `prd-planner` | `after_complete` | self-improving-agent (bg), session-logger (auto) |
| `self-improving-agent` | `before_start`, `after_complete` | session-logger, create-pr (ask_first) |
| `create-pr` | `after_complete` | session-logger (auto) |
| `debugger` | `after_complete` | self-improving-agent (bg), session-logger (auto) |
| `code-reviewer` | `after_complete` | self-improving-agent (bg), session-logger (auto) |
| `refactoring-specialist` | `after_complete` | self-improving-agent (bg), session-logger (auto) |
| `session-logger` | none | (chain terminator) |

## Hook Format Specification

### In Skill Front Matter (Actual Implementation)

Skills define hooks in their YAML front matter under `metadata.hooks`:

```yaml
---
name: my-skill
description: Skill description
allowed-tools: Read, Write, Edit, Bash, Grep
hooks: []  # Optional: declare this skill has no hooks
metadata:
  hooks:
    before_start:
      - trigger: session-logger
        mode: auto
        reason: "Log skill initiation"
    after_complete:
      - trigger: self-improving-agent
        mode: background
        reason: "Learn from successful execution"
      - trigger: session-logger
        mode: auto
        reason: "Save session context"
    on_error:
      - trigger: self-improving-agent
        mode: background
        reason: "Learn from failure patterns"
---
```

### Hook Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `trigger` | string | Yes | Name of the skill to trigger |
| `mode` | enum | Yes | Execution mode: `auto`, `background`, `ask_first` |
| `reason` | string | No | Human-readable reason for the hook |
| `context` | string | No | Context string with template variables |
| `condition` | string | No | Condition that must be true to trigger |

### Mode Definitions

| Mode | Behavior | Use Cases |
|------|----------|-----------|
| `auto` | Execute immediately, no user confirmation | Logging, status updates, background saves |
| `background` | Execute asynchronously, don't wait for completion | Learning, analysis, reflection |
| `ask_first` | Prompt user for confirmation before executing | PR creation, deployments, destructive actions |

## Workflow Chains

### PRD Creation Chain

```
prd-planner completes
    ├──▶ self-improving-agent (background) → Learns PRD patterns
    │       └──▶ create-pr (ask_first) → If skills modified
    │               └──▶ session-logger (auto)
    └──▶ session-logger (auto) → Saves context
```

### Implementation & Review Chain

```
code-reviewer completes
    ├──▶ self-improving-agent (background) → Learns review patterns
    └──▶ session-logger (auto) → Logs review

self-improving-agent completes
    ├──▶ create-pr (ask_first) → If skills were modified
    └──▶ session-logger (auto) → Logs improvement
```

### Debugging Chain

```
debugger completes
    ├──▶ self-improving-agent (background) → Learns debugging patterns
    └──▶ session-logger (auto) → Saves debugging session
```

## Template Variables

Context strings support these template variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `{skill_name}` | Name of the triggering skill | `prd-planner` |
| `{feature_name}` | Feature being worked on | `user-authentication` |
| `{prd_file}` | PRD file path | `docs/auth-prd.md` |
| `{pr_title}` | Pull request title | `feat: add user auth` |

## Implementation Guide

### For Skill Authors

To add auto-trigger capability to your skill:

1. **Add metadata.hooks** to your skill's front matter
2. **Choose appropriate modes** based on the action's importance
3. **Provide clear reasons** for each hook
4. **Test the chain** to ensure it terminates properly

### For Workflow Orchestrator

The workflow-orchestrator skill executes these hooks:

1. **On skill completion:** Check `metadata.hooks.after_complete`
2. **On skill start:** Check `metadata.hooks.before_start`
3. **On error:** Check `metadata.hooks.on_error`
4. **Respect modes:** Auto = immediate, Background = async, Ask_first = confirm
5. **Pass context:** Include trigger skill name and any template variables

## Important Rules

1. **Chain Termination:** Every chain MUST eventually terminate. `session-logger` should never trigger another skill.
2. **User Confirmation:** Use `ask_first` for any action that modifies external state (PRs, deployments, writes).
3. **Background for Learning:** Use `background` for self-improving-agent and other analysis tasks.
4. **Auto for Logging:** Use `auto` for session-logger and status updates.
5. **Avoid Recursion:** Don't create circular dependencies (e.g., A→B→C→A).

## Current Hook Inventory

```yaml
# Skills with after_complete hooks
prd-planner:
  after_complete:
    - trigger: self-improving-agent
      mode: background
      reason: "Extract patterns and improve PRD quality"
    - trigger: session-logger
      mode: auto
      reason: "Save session context"

self-improving-agent:
  before_start:
    - trigger: session-logger
      mode: auto
      context: "Start {skill_name}"
  after_complete:
    - trigger: create-pr
      mode: ask_first
      condition: skills_modified
      reason: "Submit improvements to repository"
    - trigger: session-logger
      mode: auto
      context: "Self-improvement cycle complete"

create-pr:
  after_complete:
    - trigger: session-logger
      mode: auto
      reason: "Log PR creation"

debugger:
  after_complete:
    - trigger: self-improving-agent
      mode: background
      reason: "Learn from debugging patterns"
    - trigger: session-logger
      mode: auto
      reason: "Log debugging session"

code-reviewer:
  after_complete:
    - trigger: self-improving-agent
      mode: background
      reason: "Learn from review patterns"
    - trigger: session-logger
      mode: auto
      reason: "Log review activity"

refactoring-specialist:
  after_complete:
    - trigger: self-improving-agent
      mode: background
    - trigger: session-logger
      mode: auto

# Chain Terminator
session-logger:
  # No hooks - terminates all chains
```

## Important Rules

1. **Chain Termination:** Every chain MUST eventually terminate. `session-logger` should never trigger another skill.
2. **User Confirmation:** Use `ask_first` for any action that modifies external state (PRs, deployments, writes).
3. **Background for Learning:** Use `background` for self-improving-agent and other analysis tasks.
4. **Auto for Logging:** Use `auto` for session-logger and status updates.
5. **Avoid Recursion:** Don't create circular dependencies (e.g., A→B→C→A).
