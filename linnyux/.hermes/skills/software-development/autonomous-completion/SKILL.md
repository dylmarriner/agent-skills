---
name: autonomous-completion
description: Fully autonomous end-to-end task execution and debugging. Use when the user wants one task carried from start to verified finish without intermediate check-ins, progress chatter, status updates, or “what should I do next?” pauses. Make sure to use this skill whenever the user says to keep working, continue, finish it, do it all, work silently, fix issues on your own, or not talk again until the task is 100% verified. This skill is especially appropriate when the user gives only a roadmap and expects you to build, test, and debug autonomously for as long as needed. If you encounter a hard blocker, fix what you can immediately and continue without narrating it unless the task is genuinely impossible without the user.
metadata:
  author: OpenClaw
  version: 1.3.0
  category: software-development
---

# Autonomous Completion

Use this skill when the user wants the task finished end-to-end with no conversational detours.

## Core intent

The user is not asking for a partial pass, a checkpoint, or a running commentary. They want an outcome: inspect, plan, execute, verify, repair failures, and keep going until the result is actually done.

## Operating rules

1. Restate the exact task and the finish line once, then move.
2. Create a short plan and execute it immediately.
3. Gather prerequisites before changing anything.
4. Work continuously until the task is verified complete.
5. Fix failures as they appear; do not stop at the first visible error.
6. If one fix exposes another issue, treat it as part of the same job and keep going.
7. Prefer fixing the problem over explaining it.
8. Keep working silently through follow-on failures unless you truly need user input.
9. Verify success with tools, tests, or live runtime checks.
10. Only speak when the task is truly complete or a real user decision is unavoidable.

## Debugging workflow

### 1) Inspect the real system
- Read the relevant files, routes, components, scripts, logs, or runtime state before editing.
- Prefer live verification over inference.
- If the issue is browser/app related, verify the actual browser session, not just the code.

### 2) Fix the concrete failure
- Patch the smallest thing that explains the observed failure.
- If the first patch doesn’t fully solve it, keep debugging immediately.
- Do not assume the first visible symptom is the root cause.

### 3) Verify in the same environment the user cares about
- For web apps, verify in a fresh browser session.
- Check the real request/response path, token/storage persistence, and the actual route or UI transition.
- If a browser session becomes stale, blank, or suspicious, reset it and retest before concluding anything.

### 4) Continue until success or a true external blocker
- If the task is still incomplete, keep working.
- If a hard blocker appears, repair what you can and continue silently.
- Only ask the user for help if their input is genuinely required to proceed.

## Communication style

When this skill is active, default to:
- no status updates
- no progress chatter
- no issue summaries mid-task
- no “here’s what I found” narration unless the user must decide something
- final response only after verified completion

## Good fits

Use this for requests like:
- “keep working until it’s fully fixed”
- “don’t stop until the whole flow works”
- “debug this end-to-end and only tell me when it’s done”
- “work silently and fix whatever you find”
- “build, test, and debug this from the roadmap”
- “I don’t want to hear about blockers, just get it done”

## What not to do

- Don’t turn a full task into a tiny checkpoint.
- Don’t stop after fixing only the first visible error.
- Don’t narrate intermediate blockers unless the user truly has to choose.
- Don’t claim success without a real verification step.
- Don’t wait for permission when the next step is obvious and within scope.

## Why it matters

This keeps the agent focused on the user’s real intent: not a partial attempt, but a verified result.

## Notes for browser/app debugging

- Verify the live UI path in a fresh browser session before blaming code.
- If backend/API behavior is correct but the UI does not transition, inspect the browser-side request, storage, and navigation path directly.
- If the browser appears empty, stale, or broken, reset the session and retest.
- When a request succeeds in the backend but the UI still fails, check whether the frontend is actually persisting the auth state and whether the app is rehydrating from the right storage layer.
- If a browser/web app mounts to a blank page, inspect the page root, bundle load, and browser console before assuming the navigation/auth logic is wrong.
- For auth flows specifically, distinguish “backend returned a token” from “browser persisted and rehydrated the token.” Treat the latter as the real success criterion for UI transitions.
- If the browser session keeps becoming empty or inconsistent after reloads, restart the web runtime and retest rather than trying to infer state from a poisoned session.
- If the page title changes but the root stays empty, suspect a bootstrap/runtime mismatch or an import-time render crash before blaming the API.
- When a web app is unexpectedly blank, inspect the entrypoint, router assumptions, top-level imports, and any recently edited hooks or native-only dependencies before changing deeper business logic.
- If a router-root or framework shell appears instead of the actual app, verify whether the build is still influenced by stale router dependencies or cached web artifacts, and clean/restart before concluding the app code is wrong.
- Avoid duplicate or conflicting auth transitions: prefer a single source of truth for auth state and navigation so imperative resets do not fight declarative rerenders.
- When a login flow fails in the browser, verify the handler fired, the network request succeeded, the token was written, and the navigator rehydrated in that order.
- Keep fixing the app code and retest in a clean session, but do not report intermediate diagnostics unless the user explicitly asked for them.
- If the user explicitly wants no chatter/status updates, treat silence as a requirement: keep working, repair blockers, and only speak when the task is actually complete or a true decision is needed.
- If the user gives only a roadmap and expects autonomous build/test/debug execution, assume a long-running end-to-end workflow is desired and keep iterating until success or a hard external blocker is proven.
- Do not let a first “mostly working” browser result end the task; require a verified end-to-end user-facing transition before declaring success.
