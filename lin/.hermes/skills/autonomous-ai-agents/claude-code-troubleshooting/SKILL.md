---
name: claude-code-troubleshooting
description: "Diagnose and fix Claude Code auth, session persistence, startup, and CLI breakage. Use when claude logs out after auth, sessions don't resume, session dir stays empty, or auth status disagrees with runtime behavior."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Claude, debugging, auth, sessions, cli]
    related_skills: [claude-code, hermes-agent]
---

# Claude Code Troubleshooting

Use this skill when `claude` claims login succeeds but behaves unauthenticated, drops the session on startup, or fails to persist/resume sessions.

## Decision Tree

1. `claude auth status --text` shows logged in?
   - YES → problem is session/runtime/auth-store, not credentials.
   - NO  → run `claude auth login` and re-test.

2. Token actually expired?
   - Check `~/.claude/.credentials.json` `expiresAt` ms vs current epoch ms.
   - If expired: re-auth. If not expired: token-store is fine.

3. Session writes broken?
   - Check `~/.claude/sessions/` is non-empty after an interactive run.
   - If empty: session persistence is broken. Check:
     - disk space / inodes
     - `~/.claude/` permissions
     - stale `settings.bak` being loaded by Claude's settings cascade
     - config/plugin/hook crash killing session write beforeEach shutdown

4. Hooks killing the session?
   - Validate all PreToolUse/Stop hooks in `~/.claude/settings.json` return 0 quickly.
   - Temporarily disable hooks to see if behavior changes.

## Session Persistence Checklist

- `claude auth status --text`
- `stat ~/.claude/.credentials.json`
- `ls -ld ~/.claude/sessions`
- `ls -la ~/.claude/sessions`
- `cat ~/.claude/settings.json`
- `cat ~/.claude/settings.local.json`
- `claude --version` + realpath of binary
- `claude auth login`
- run `claude` plain, no tmux, no wrapper
- monitor with `tmux capture-pane` if using tmux

## Known Patterns

- "Logged in but logs out every time" with valid token → inspect session persistence, not auth state.
- Hook scripts must exit 0 and be fast; non-zero or hangs abort Claude before session state is flushed.
- Empty `~/.claude/sessions/` after a successful interactive run indicates writes are failing silently.
- `claude --bare` bypasses OAuth entirely.
- Concurrent sessions on different devices can invalidate stored tokens depending on org policy.
