---
name: cron-job-response
description: "Patterns for responding when invoked as a cron/scheduled job — SILENT rule, delivery format, and structural conventions for headless execution."
---

# Cron Job Response Patterns

## When to load this skill

Load this whenever the user's message starts with `[IMPORTANT: You are running as a scheduled cron job]` or otherwise signals that this is a cron/scheduled/automated invocation with no user present.

## Core rules

1. **No interaction, no clarification.** There is no user to ask — execute autonomously. Make reasonable decisions without asking.

2. **Deliver output directly in your response.** The system auto-delivers your final message — do NOT use `send_message` or any other delivery mechanism. Just write the report.

3. **The [SILENT] rule** — this is the most important and most commonly violated:
   - If there is **genuinely nothing new to report** → respond with exactly the text `[SILENT]` and **nothing else**. No leading/trailing text, no explanation, no context.
   - If there **is something to report** → produce your full report/output as the response. Do NOT append `[SILENT]` to a report.
   - **Never combine [SILENT] with other content.** Either report findings normally, or say `[SILENT]` alone. The two are mutually exclusive.
   - `[SILENT]` suppresses delivery — if there's content, it needs to be delivered.

4. **Be concise.** 2-3 line summary is ideal unless the task explicitly demands a longer report.

## Workspace state assessment

When the task involves "check what's going on" or running a tick cycle, use
the **four-probe pattern** from `references/workspace-state-assessment.md`:

1. **Config probe** — grep the cron config for registered jobs (grep -i cron config.yaml)
2. **Git probe** — git status + git diff + git log in the workspace
3. **File probe** — read HEARTBEAT.md, MEMORY.md, state JSON, today's memory file
4. **Service probe** — check Synapse/Nexus/RAGFlow availability

### HEARTBEAT.md convention

The HEARTBEAT.md file controls whether work is pending:
- **Comments-only** (HTML comments or empty) → No work. Reply `[SILENT]`.
- **Actual task content** → Execute each item, report results.

Do not infer tasks from prior conversations or memory files. The heartbeat
file is the single source of truth for cron-tick work.

## Reference files

- `references/workspace-state-assessment.md` — Multi-source probe pattern for
  autonomously assessing headless workspace state. Covers config probing, git
  diff detection, HEARTBEAT.md convention, memory file reading, and service
  health checks. The primary workflow document for any cron tick that needs to
  "check what changed."
- `references/subconscious-plugin-tick.md` — How to find, import, and call the
  subconscious plugin from a cron job. Covers the actual plugin location
  (`plugins/` not `plugins.local/`), the three state files, and what tick() returns
  when the goal store is empty.

## Common pitfalls

- **SILENT + content combo**: The most frequent mistake. If you wrote a report, skip [SILENT]. If you wrote [SILENT], delete the report. One or the other.
- **Sending output via wrong channel**: Do not use `send_message`, `memory`, or any non-response mechanism for the report. The system's auto-delivery IS the channel.
- **Asking questions**: Do not ask for clarification, confirmation, or permission. There's nobody there to answer.
- **Over-reporting no-change**: "No active goals, nothing changed" → that's [SILENT] territory. Only produce a report when there was actual meaningful work.
- **Assuming module existence**: Config references a component name (e.g. 'subconscious') — never assume it's a Python import. Check filesystem for `__init__.py` first. The actual implementation may be Rust, a sidecar binary, or non-existent. Trace from config → filesystem → source code before concluding how something works. Hermes plugins live under `~/.hermes/plugins/<name>/` (user-installed, common), `~/.hermes/plugins.local/<name>/` (user-installed, alternate), or `~/.hermes/hermes-agent/plugins/<name>/` (packaged) — check both with `ls -d ~/.hermes/plugins/*/ ~/.hermes/plugins.local/*/ ~/.hermes/hermes-agent/plugins/*/`.
- **Hermes plugin modules need sys.path surgery**: A cron job says "call subconscious.tick()" and `import subconscious` fails — the module IS at a known Hermes plugin path but NOT on `sys.path`. Plugins can live in:
  - `~/.hermes/plugins/<name>/` (user-installed — common)
  - `~/.hermes/plugins.local/<name>/` (user-installed — alternate)
  - `~/.hermes/hermes-agent/plugins/<name>/` (packaged)
  - `/mnt/hermes-profile-nfs/plugins/<name>/` (NFS profile mount — active shared profile)
  Check all four with `ls -d ~/.hermes/plugins/*/ ~/.hermes/plugins.local/*/ ~/.hermes/hermes-agent/plugins/*/ 2>/dev/null | head -20`.

  Three resolution strategies, in order of robustness:

  1. **sys.path + bare import** (works when the plugin's parent dir is directly accessible):
     ```python
     sys.path.insert(0, '/home/lin/.hermes/plugins')
     import subconscious
     subconscious.tick()
     ```
     If import fails, the parent dir may be `plugins.local` instead — try:
     ```python
     sys.path.insert(0, '/home/lin/.hermes/plugins.local')
     ```

  2. **importlib.import_module** (works for dotted paths when parent is on sys.path):
     The parent dir name can be `plugins` or `plugins.local`:
     ```python
     import importlib
     # Try plugins first:
     sc = importlib.import_module('plugins.subconscious')
     ```

  3. **importlib.util.spec_from_file_location** (most robust — works regardless of sys.path, package structure, or NFS location):
     ```python
     import importlib.util
     spec = importlib.util.spec_from_file_location(
         "subconscious",
         "/path/to/plugins/subconscious/__init__.py"
     )
     mod = importlib.util.module_from_spec(spec)
     sys.modules["subconscious"] = mod
     spec.loader.exec_module(mod)
     mod.tick()
     ```
     This is the fallback when all other import strategies fail (e.g. the plugins dir has no `__init__.py`, or the path is an NFS mount not reachable via sys.path).

  Do NOT conclude "module doesn't exist" from an `ImportError` — check all three directories first, and if none match then use `find`. And do NOT use `from subconscious.__init__ import tick` — that raises `ModuleNotFoundError` because `__init__` is implicit; use the bare module name.
