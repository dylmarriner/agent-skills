---
name: change-verification
description: "Use before reporting a change as working: verify it first."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [testing, verification, debugging, build-hygiene]
    related_skills: [linux-host-performance-triage, codebase-dev]
---

# Change Verification

## When to Use

- You edited code, config, or a service surface and are about to report the result.
- A test suite failed, hung, or timed out after your change and you need to know whether you caused it.
- You widened a registry, tool list, or exported shape.
- You rebuilt something that a running app, daemon, or MCP/agent tool surface serves.

Applies to any repo, with or without a full test suite, and to running daemons, apps, and MCP/agent tool surfaces.

## Prove causality before you fix anything

- When a suite fails after your edit, isolate it: `git stash push -- <path to your file>`, re-run the failing suite, `git stash pop`. Stash the single path, not the tree — unrelated uncommitted work usually sits alongside yours and a bare `git stash` hides it.
- Confirm the baseline is green at HEAD before you believe the failure is pre-existing. "It was already broken" is a claim that needs one command behind it.
- After the fix, run the FULL suite, not only the file you touched. The failure you repaired can be masking others behind it.
- Do not report a green result from a narrower check than the change's blast radius. A typecheck passing says nothing about a test that asserts a list you changed.

## A hang is a leaked handle, not a slow test

- A suite that hangs, or reports a setup/`beforeAll` timeout, is usually an assertion that threw mid-test before teardown ran: the leaked client, socket, or handle keeps the runner alive with nothing left to log.
- Fix the assertion. Do not raise the test timeout, and do not hunt open handles first — that diagnoses the symptom the broken assertion created.

## Exact-shape assertions and hand-rolled mocks

- Grep the test tree for the symbol BEFORE widening a registry, tool list, or exported shape: `rg -l '<symbol>' --glob '**/__tests__/**'`. Mocks reimplement the old shape and exact-list assertions encode it, so they fail in a file you never opened.
- Update the exact-list assertion in the same change as the registry. Loosening or deleting it is not the fix — it is the only thing guarding that surface.
- Enumerate the callee's real method declarations before wrapping a call. A dependency object typed `any` compiles happily around a signature that was never implemented, and it fails only at runtime.

## Build and run hygiene

- Do not run a build script that deletes the output tree first (`rm -rf dist && tsc`) while an app or daemon has those modules loaded. Invoke the compiler directly (`tsc -p .`) so it emits over the tree with no window where the artifact is missing; reserve the clean build for when nothing is running.
- A process keeps the code it already loaded. A rebuild changes nothing until the process restarts — say that plainly instead of implying the running instance picked up your change.

## Process hygiene

- `pkill -f '<pattern>'` matches its own command line and kills the shell running it, silently skipping every command after it in the sequence. Use the bracket form (`pkill -f '[j]est'`) or `pgrep -f` plus kill by pid, and put cleanup in its own call.
- When a multi-command sequence exits early or reports a signal, assume the later commands never ran and re-verify their effects; do not read a partial transcript as success.

## Prove a service or tool surface end-to-end

- The service's own endpoint is ground truth for liveness and auth: `401` means it is alive and rejecting the credential, `000` or connection-refused means nothing is listening on that port.
- A successful registration or config write is NOT proof the target is reachable. Registration records a URL or command and nothing more.
- Send one well-formed wrong credential and expect rejection — the cheapest proof the auth path is real rather than cosmetic.
- Read state back from the source of truth (the server, the daemon, the database) rather than from a client's cached view, and say which of the two you checked.
- A server caches the tool list it advertised at connect time, and a running server keeps the code it loaded — after extending a server's tool registry, the server must be relaunched and every client reconnected before the new surface exists anywhere.

## Report shape

- Before/after evidence, not adjectives: measured numbers, exit codes, counts.
- One line per change with its revert command.
- What you deliberately did NOT touch, and why.
- What still needs a human action (restart, relaunch, approval) called out separately from what is already live.
- If something is unproven, say it is unproven. "Exists but not verified" and "verified" are different claims.

## One-line rule

Never claim a change works on the strength of a check that could not have failed.
