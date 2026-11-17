---
name: app-launch-verification
description: Use when starting a repo's app and verifying it came up.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  category: software-development
  hermes:
    tags: [launch, entry-point, verification, electron, dev-server, ports]
    related_skills: [project-survey-and-orientation, autonomous-completion]
---

# App Launch & Verification

## When to Use

Use when asked to "start the app", "run the project", "get it up", "bring it up", or
otherwise launch a repository's application — and use it again whenever a launch must
be *confirmed* rather than assumed. Pairs with `project-survey-and-orientation` (locate
and survey) — this skill is the launch-and-prove half.

## Procedure

### 1. Read the repo's recorded launch path before inventing one

Order of authority: `README` / `MANIFEST` / `BUILD_INSTRUCTIONS` → root `package.json`
`scripts` → `Makefile` targets → a launcher script at the repo root → the entry point
file itself. Do not hand-roll a launch command when the repo records one; the recorded
one wires up the pieces you do not know about.

### 2. Decide which entry point is the complete application

Mature repos hold several runnable entry points at once. Signals that separate the
current stack from the legacy one:

- **Build artifacts exist and are fresh** for one stack (`dist/`, `target/`,
  packaged sidecars, installed `node_modules`) and another entry point has none.
- **The launcher supervises the other processes.** If one command starts the UI *and*
the backend/API sidecar, that is the complete application; a standalone GUI or dev
server beside it is a leftover.
- **The feature set matches what the user described.** Ask which screens/services they
  mean before picking.

### 3. Launch from the repo root, tracked as a real process

Use a tracked background process for anything long-lived, not a shell-level background
wrapper, so liveness can be checked afterwards. Keep the launch command identical to
the recorded one (add only flags the recorded command documents).

### 4. Verify with evidence, in this ladder

1. **The app's own readiness signal** — health/status endpoint, or the child services
   it is supposed to have spawned (API sidecar, renderer, backend).
2. **Process tree** — confirm the parent *and* its children are alive, not just that a
   shell returned.
3. **A screenshot** for anything with a UI, so you can state what is actually on
   screen rather than which window was requested.

Only then report it as running.

### 5. Report state, including strays

Say what is running, on which ports, and what you started while probing. Anything you
launched that the user did not ask for is a stray holding a port — offer to stop it, or
stop it.

## Pitfalls

- **Launch scripts are often committed without the executable bit.**
  `Permission denied` means `chmod +x` or invoke through the interpreter — it does not
  mean the script is broken.
- **A subdirectory entry point that imports top-level packages fails by file path.**
  `ModuleNotFoundError: No module named '<pkg>'` happens because the script's own
  directory lands on `sys.path`, not the repo root. Run it as a module from the root:
  `python -m <pkg>.<entry>`. Prefer that over editing the file to add a `sys.path`
  bootstrap — the launcher problem is not a code problem.
- **A background process can exit instantly and still report a clean shell status.**
  A returned command is not a running app; check the process and, if it died, run it in
  the foreground with a short timeout to capture the real traceback before concluding.
- **A port being busy does not mean the app is already up.** Another service can answer
  on that port with a 200 (or a 404 in a different shape). Curl the endpoint and inspect
  the payload before deciding, then move the launch to a free port.
- **Several GUIs coexist and the wrong one looks plausible.** A small legacy window can
  come up perfectly and still be the wrong application; if the user says it is not the
  one, re-identify from their described features and start the other stack instead of
defending the first launch — and shut down the half-right instance.
- **A GUI that renders then exits is a failed launch.** Confirm the process outlives the
  first render. For a split UI/API app, inspect the API's own log before interpreting
  frontend proxy errors: the UI can render while the backend has already exited.
- **A backend that requires a live provider is not ready merely because its process was
  spawned.** When startup says no inference engine/provider is available, verify the
  configured engine's health and required credentials in the same environment used to
  launch it, then retry and confirm the API health endpoint before reopening the UI.
- **Do not claim success from a startup log line.** Startup logs and "initializing"
  messages are written before the failure they precede; the readiness signal is the
  evidence.
