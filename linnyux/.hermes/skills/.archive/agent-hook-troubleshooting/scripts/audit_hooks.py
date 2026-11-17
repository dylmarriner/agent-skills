#!/usr/bin/env python3
"""Audit every Codex hook command by actually executing it, and report failures.

Codex reports one hook failure at a time and only as an exit code. This walks
all hook sources -- the user hooks.json, inline [hooks] in config.toml, and each
plugin's bundled hooks per cached version -- runs each command the way Codex
does, and prints the exit code plus the first stderr line.

Run it under the restrained PATH a desktop-app launch provides, which is where
most 127s come from:

    PATH=/usr/bin:/bin:/usr/local/bin python3 audit_hooks.py

Exit status is 0 when every hook succeeded, 1 otherwise, so it can gate a fix.
"""
import glob
import json
import os
import subprocess
import sys

HOME = os.path.expanduser("~")
CODEX = os.path.join(HOME, ".codex")

PAYLOAD = json.dumps({
    "hook_event_name": "SessionStart",
    "session_id": "hook-audit",
    "cwd": "/tmp",
    "source": "startup",
})


def sources():
    """Every hook file to inspect, as (label, path, plugin_root_or_None)."""
    out = []
    user_hooks = os.path.join(CODEX, "hooks.json")
    if os.path.exists(user_hooks):
        out.append(("user hooks.json", user_hooks, CODEX))

    pattern = os.path.join(CODEX, "plugins", "cache", "*", "*", "*", "hooks", "*.json")
    for path in sorted(glob.glob(pattern)):
        parts = path.split(os.sep)
        try:
            idx = parts.index("cache")
        except ValueError:
            continue
        label = "%s@%s" % (parts[idx + 2], parts[idx + 1])
        out.append((label, path, os.path.dirname(os.path.dirname(path))))
    return out


def inline_hooks():
    """Inline [hooks] commands in config.toml that are not the state table."""
    try:
        import tomllib
    except ImportError:
        return []
    path = os.path.join(CODEX, "config.toml")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "rb") as fh:
            cfg = tomllib.load(fh)
    except Exception:
        return []
    hooks = cfg.get("hooks") or {}
    found = []
    for event, groups in hooks.items():
        if event == "state" or not isinstance(groups, list):
            continue
        for group in groups:
            for hook in group.get("hooks", []):
                if hook.get("command"):
                    found.append(("config.toml [hooks] %s" % event, hook["command"]))
    return found


def run(label, event, cmd, plugin_root, timeout):
    env = dict(os.environ)
    if plugin_root:
        env["PLUGIN_ROOT"] = plugin_root
        env["CLAUDE_PLUGIN_ROOT"] = plugin_root
    try:
        proc = subprocess.run(
            ["bash", "-c", cmd],
            input=PAYLOAD.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd="/tmp",
            timeout=timeout,
        )
        code = proc.returncode
        err = (proc.stderr.decode(errors="replace").strip().splitlines() or [""])[0]
    except subprocess.TimeoutExpired:
        code, err = "TIMEOUT", ""
    ok = code == 0
    print("  %-20s exit=%-8s %s%s" % (event, code, err[:100], "" if ok else "   <-- FAILS"))
    if not ok:
        print("      cmd: %s" % cmd[:160].replace("\n", " "))
    return ok


def main():
    inspected = []
    failures = 0
    for label, path, plugin_root in sources():
        if path in inspected:
            continue
        inspected.append(path)
        try:
            with open(path) as fh:
                doc = json.load(fh)
        except Exception as exc:
            print("== %s\n   unreadable: %s" % (label, exc))
            failures += 1
            continue
        print("== %s\n   %s" % (label, path))
        for event, groups in (doc.get("hooks") or {}).items():
            for group in groups:
                for hook in group.get("hooks", []):
                    cmd = hook.get("command")
                    if not cmd:
                        continue
                    timeout = int(hook.get("timeout", 30)) + 15
                    if not run(label, event, cmd, plugin_root, timeout):
                        failures += 1

    inline = inline_hooks()
    if inline:
        print("== config.toml [hooks]")
        for event, cmd in inline:
            if not run("config.toml", event, cmd, CODEX, 45):
                failures += 1

    print()
    print("failures: %d" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
