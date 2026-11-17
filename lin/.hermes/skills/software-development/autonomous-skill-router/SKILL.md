---
name: autonomous-skill-router
description: Route every substantive task to the most relevant workflow skills before execution. Use this whenever a user request may benefit from autonomous completion, memory integration, self-improvement, planning, debugging, code review, or other reusable workflows. Prefer loading the full autonomous execution stack whenever a request is multi-step, build/test/debug oriented, or likely to need iteration.
metadata:
  author: OpenClaw
  version: 1.0.0
  category: software-development
---

# Autonomous Skill Router

Use this skill before starting a task when you want a quick decision about which workflow skills should be loaded.

## Routing rules

- If the task is multi-step or end-to-end, include `autonomous-completion`.
- If the task may benefit from durable context, past lessons, or MCP-backed memory, include `custom-memory-mcp-integration`.
- If the task involves learning from mistakes, workflow refinement, or non-trivial execution, include `self-improvement`.
- If the task is a large implementation or needs a strict startup sequence, include `autonomous-starter-checklist`.

## Output

Return a standardized recommendation in this format:

Load order:
1. [skill name]
2. [skill name]
3. ...

Only include the skills that actually apply to the task.

Example:
Load order:
1. autonomous-starter-checklist
2. autonomous-completion
3. custom-memory-mcp-integration
4. self-improvement

## Why it helps

It reduces setup friction by mapping task shape to the right reusable workflows before execution begins.
