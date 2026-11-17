---
name: autonomous-starter-checklist
description: Pre-flight checklist for big tasks that loads autonomous completion, custom memory integration, and self-improvement workflows before execution.
metadata:
  author: OpenClaw
  version: 1.0.0
  category: software-development
---

# Autonomous Starter Checklist

Use this skill before starting a large, multi-step task.

## Purpose

This skill ensures the agent begins with the right execution and learning workflows already in place:
- autonomous-completion
- custom-memory-mcp-integration
- self-improvement

## Steps

1. Consult autonomous-skill-router to identify the matching workflows.
2. Consult the current skills list and confirm the needed skills exist.
3. Restate the exact user task.
4. Load autonomous-completion.
5. Load custom-memory-mcp-integration when the task may benefit from durable context or stored lessons.
6. Load self-improvement before non-trivial work so lessons and playbook guidance are available.
7. Confirm the plan covers discovery, implementation, verification, and final reporting.
8. Begin execution and continue until the task is actually complete.

## Use when

- The user asks for a big task or end-to-end implementation.
- The task will take multiple steps.
- The task benefits from durable memory or reusable lessons.

## Why it helps

It gives the agent a consistent pre-flight sequence so it does not start executing before the right workflows are active.
