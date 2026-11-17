---
name: message-skill-router
description: Route every user message to the right installed skills by classifying the request into a task category, then loading the relevant workflow skills before execution. Use this when the user wants the assistant to automatically determine the task type, choose applicable skills, and avoid manual skill selection. Especially use this for build/test/debug requests, roadmap-only implementation requests, QA, coding, refactoring, automation, and any message that should be routed to autonomous completion or another specialized workflow.
metadata:
  author: OpenClaw
  version: 1.0.0
  category: software-development
---

# Message Skill Router

Use this skill as the front door for every substantive message. The goal is to classify the request first, then load the best-fit workflow skills before doing any real work.

## Purpose

The user is asking for automatic skill selection. Do not make them choose workflows manually if the task can be classified from the message itself.

## Classification steps

1. Read the user message and identify the primary task category.
2. Decide whether the request is one of the following:
   - end-to-end build / test / debug
   - roadmap / planning / specification
   - code review / verification
   - refactor / cleanup / maintenance
   - QA / browser / app testing
   - memory / session / autonomous learning
   - multi-agent / delegation / long-running work
3. Load the relevant skills for that category.
4. If the message is multi-step, implementation-oriented, or likely to require iteration, always include `autonomous-completion`.
5. If the task is large or benefits from a startup sequence, include `autonomous-starter-checklist`.
6. If the task may benefit from durable context or learned lessons, include the relevant memory or self-improvement workflows.
7. If the task is about the codebase or app behavior, include the debugging or QA workflow that best matches it.
8. If the request is ambiguous but clearly substantive, prefer loading the broader autonomous stack rather than waiting for more clarification.
9. If the message looks like routine conversational filler with no actionable task, do not over-route it.

## Routing priorities

When in doubt, prefer broader autonomous workflows over narrow one-off actions, because the user asked for the system to pick the right tools and keep going.

### Always consider
- `autonomous-completion`
- `autonomous-starter-checklist`
- `autonomous-skill-router`
- `skills-hub-scout`
- `self-improvement`
- `custom-memory-mcp-integration`
- `session-logger`

### Default meta-workflows for substantive messages
- Always include `self-improvement` when the task is non-trivial or involves debugging, planning, or iterative work.
- Always include `custom-memory-mcp-integration` when the task may benefit from durable memory, repeated lessons, or cross-session continuity.
- Always include `session-logger` when the user is working on a long-running or multi-step task so the session can be persisted.
- Always include `autonomous-completion` when the task is multi-step, implementation-oriented, or likely to require iteration.

### Add when relevant
- `systematic-debugging`
- `test-driven-development`
- `writing-plans`
- `requesting-code-review`
- `subagent-driven-development`
- `dogfood`
- `webapp-testing`
- `session-handoff`

### Add when relevant
- `systematic-debugging`
- `test-driven-development`
- `writing-plans`
- `requesting-code-review`
- `subagent-driven-development`
- `dogfood`
- `webapp-testing`
- `session-logger`
- `session-handoff`

## Output

Return the recommended skill load order as a plain list, with the most important workflow first.

Example:
1. autonomous-starter-checklist
2. autonomous-skill-router
3. autonomous-completion
4. custom-memory-mcp-integration
5. self-improvement

## Why it matters

This reduces back-and-forth and lets the assistant pick the right reusable workflows automatically from the user’s message instead of asking them to do the routing manually.
