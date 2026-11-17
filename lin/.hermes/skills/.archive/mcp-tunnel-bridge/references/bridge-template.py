#!/usr/bin/env python3
"""HERMES MCP BRIDGE — OMNISCIENT MODE — MULTI-DEVICE.

Deploy this on each machine you want to expose through the tunnel.
Set HERMES_MCP_PREFIX env var for a clean hostname (e.g. "lin", "kubuntux").
See mcp-tunnel-bridge SKILL.md for full deployment instructions.
"""

import asyncio
import contextlib
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# ── Override env vars for omni mode ─────────────────────────────
os.environ.setdefault("HERMES_CRON_SESSION", "approve")
os.environ.setdefault("HERMES_EXEC_ASK", "0")
os.environ.setdefault("HERMES_MCP_EXCLUDE_TOOLSETS", "")

# ── Import triggers registry discovery ─────────────────────────
import model_tools  # noqa: F401
from tools.registry import registry

# ── Auto-approve all commands (backward compat w/ Hermes 0.17) ──
try:
    from tools.approval import set_hermes_interactive_context
    _interactive_token = set_hermes_interactive_context(True)
except ImportError:
    pass  # Hermes < 0.18

from tools.terminal_tool import set_approval_callback, set_sudo_password_callback

def _always_approve(_command: str) -> dict:
    return {"approved": True, "message": None}

def _sudo_password_prompt(_prompt_text: str = "") -> str:
    try:
        from tools.terminal_tool import _get_cached_sudo_password
        pw = _get_cached_sudo_password()
        return pw or "root"
    except Exception:
        return "root"

set_approval_callback(_always_approve)
set_sudo_password_callback(_sudo_password_prompt)

# ── Hostname prefix ─────────────────────────────────────────────
_HERMES_MCP_PREFIX_ENV = os.environ.get("HERMES_MCP_PREFIX")
if _HERMES_MCP_PREFIX_ENV:
    HOSTNAME = _HERMES_MCP_PREFIX_ENV
else:
    HOSTNAME = socket.gethostname().split(".")[0]
PREFIX = HOSTNAME.lower().replace("-", "_").replace(" ", "_")

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logger = logging.getLogger("hermes-mcp-bridge")

EXCLUDE_TOOLSETS: set[str] = set()
HERMES_BIN = os.environ.get("HERMES_MCP_BIN") or shutil.which("hermes") or "hermes"
ASK_DEFAULT_TIMEOUT = int(os.environ.get("HERMES_MCP_ASK_TIMEOUT_SEC", "300"))

DIRECT_DISPATCH_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {"result": {}, "raw_text": {"type": "string"}},
    "required": ["result", "raw_text"],
}

SYSTEM_EXEC_TOOL_NAME = f"{PREFIX}_system_exec"
SYSTEM_EXEC_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {"type": "string", "description": f"Raw shell command on {HOSTNAME}. Full access."},
        "timeout_sec": {"type": "integer", "description": "Max seconds (default 60, max 600)."},
        "workdir": {"type": "string", "description": "Working directory (defaults to /tmp)."},
    },
    "required": ["command"],
}
SYSTEM_EXEC_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "stdout": {"type": "string"}, "stderr": {"type": "string"},
        "exit_code": {"type": "integer"}, "timed_out": {"type": "boolean"},
    },
}

HERMES_ASK_TOOL_NAME = f"{PREFIX}_hermes_ask"
HERMES_ASK_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "prompt": {"type": "string", "description": f"Task for Hermes agent on {HOSTNAME}."},
        "session_id": {"type": "string"},
        "model": {"type": "string"},
        "toolsets": {"type": "string"},
        "timeout_sec": {"type": "integer", "description": f"Default {ASK_DEFAULT_TIMEOUT}."},
    },
    "required": ["prompt"],
}
HERMES_ASK_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {"type": "string"},
        "session_id": {"type": ["string", "null"]},
        "model": {"type": ["string", "null"]},
        "provider": {"type": ["string", "null"]},
        "estimated_cost_usd": {"type": ["number", "null"]},
        "total_tokens": {"type": ["integer", "null"]},
        "completed": {"type": ["boolean", "null"]},
        "error": {"type": "string"},
        "returncode": {"type": "integer"},
        "stderr": {"type": "string"},
    },
    "required": ["response"],
}

server: Server = Server(f"hermes-omni-{PREFIX}")

def _schema_to_mcp(func_schema: dict) -> dict:
    params = func_schema.get("parameters") or {"type": "object", "properties": {}}
    if params.get("type") != "object":
        params = {"type": "object", "properties": {}}
    params.setdefault("properties", {})
    return params

def _eligible_tool_names() -> list[str]:
    all_names = set(registry.get_all_tool_names())
    if EXCLUDE_TOOLSETS:
        all_names = {n for n in all_names if registry.get_toolset_for_tool(n) not in EXCLUDE_TOOLSETS}
    return sorted(all_names)

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    names = _eligible_tool_names()
    defs = registry.get_definitions(set(names), quiet=True)
    tools = []
    for d in defs:
        fn = d["function"]
        prefixed_name = f"{PREFIX}_{fn['name']}"
        tools.append(types.Tool(
            name=prefixed_name,
            description=f"[{HOSTNAME}] {fn.get('description') or fn['name']}",
            inputSchema=_schema_to_mcp(fn),
            outputSchema=DIRECT_DISPATCH_OUTPUT_SCHEMA,
        ))
    # system_exec
    tools.append(types.Tool(
        name=SYSTEM_EXEC_TOOL_NAME,
        description=f"[{HOSTNAME}] RAW SHELL on {HOSTNAME}. No security checks.",
        inputSchema=SYSTEM_EXEC_INPUT_SCHEMA,
        outputSchema=SYSTEM_EXEC_OUTPUT_SCHEMA,
    ))
    # hermes_ask
    tools.append(types.Tool(
        name=HERMES_ASK_TOOL_NAME,
        description=f"[{HOSTNAME}] Full Hermes agent turn (costs tokens).",
        inputSchema=HERMES_ASK_INPUT_SCHEMA,
        outputSchema=HERMES_ASK_OUTPUT_SCHEMA,
    ))
    logger.warning("OMNI %s: %d direct tools + system_exec + hermes_ask", HOSTNAME, len(tools) - 2)
    return tools

async def _run_system_exec(arguments: dict) -> dict:
    command = arguments.get("command", "")
    if not command:
        return {"stdout": "", "stderr": "command required", "exit_code": 1, "timed_out": False}
    timeout = min(int(arguments.get("timeout_sec", 60)), 600)
    workdir = arguments.get("workdir", "/tmp")
    try:
        proc = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=workdir)
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            timed_out = False
        except asyncio.TimeoutError:
            proc.kill()
            stdout_b, stderr_b = await proc.communicate()
            timed_out = True
        return {"stdout": stdout_b.decode("utf-8", errors="replace"),
                "stderr": stderr_b.decode("utf-8", errors="replace"),
                "exit_code": proc.returncode or 0, "timed_out": timed_out}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": -1, "timed_out": False}

async def _run_hermes_ask(arguments: dict) -> dict:
    prompt = arguments.get("prompt")
    if not prompt:
        return {"response": "", "error": "prompt required"}
    session_id = arguments.get("session_id")
    model = arguments.get("model")
    toolsets = arguments.get("toolsets")
    timeout_sec = int(arguments.get("timeout_sec") or ASK_DEFAULT_TIMEOUT)
    with tempfile.TemporaryDirectory(prefix="hermes-mcp-ask-") as tmp:
        usage_path = Path(tmp) / "usage.json"
        argv = [HERMES_BIN, "-z", prompt, "--accept-hooks", "--usage-file", str(usage_path)]
        if session_id: argv += ["--resume", session_id]
        if model: argv += ["-m", model]
        if toolsets: argv += ["-t", toolsets]
        try:
            proc = await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
        except asyncio.TimeoutError:
            proc.kill()
            return {"response": "", "error": f"timed out after {timeout_sec}s"}
        except FileNotFoundError:
            return {"response": "", "error": f"hermes not found: {HERMES_BIN}"}
        stdout_text = stdout_b.decode("utf-8", errors="replace").strip()
        stderr_text = stderr_b.decode("utf-8", errors="replace").strip()
        usage = {}
        if usage_path.exists():
            try: usage = json.loads(usage_path.read_text())
            except (OSError, json.JSONDecodeError): pass
        response = {"response": stdout_text, "session_id": usage.get("session_id"),
                    "model": usage.get("model"), "provider": usage.get("provider"),
                    "estimated_cost_usd": usage.get("estimated_cost_usd"),
                    "total_tokens": usage.get("total_tokens"), "completed": usage.get("completed")}
        if proc.returncode != 0 or usage.get("failed"):
            response["error"] = "hermes run failed"; response["returncode"] = proc.returncode; response["stderr"] = stderr_text[-2000:]
        return response

@server.call_tool()
async def call_tool(name: str, arguments: dict | None):
    arguments = arguments or {}
    if name == SYSTEM_EXEC_TOOL_NAME:
        result = await _run_system_exec(arguments)
        raw_text = json.dumps(result, ensure_ascii=False)
        return [types.TextContent(type="text", text=raw_text)], result
    if name == HERMES_ASK_TOOL_NAME:
        return await _run_hermes_ask(arguments)
    # Strip prefix to get original Hermes tool name
    original_name = name
    if name.startswith(f"{PREFIX}_"):
        original_name = name[len(PREFIX) + 1:]
    result = registry.dispatch(original_name, arguments, task_id="mcp-bridge", session_id="mcp-bridge", user_task="")
    if isinstance(result, dict):
        raw_text = json.dumps(result, ensure_ascii=False); parsed = result
    else:
        raw_text = result
        try: parsed = json.loads(result)
        except (TypeError, json.JSONDecodeError): parsed = result
    structured = {"result": parsed, "raw_text": raw_text}
    return [types.TextContent(type="text", text=raw_text)], structured

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, InitializationOptions(
            server_name=f"hermes-omni-{PREFIX}", server_version="0.1.0",
            capabilities=server.get_capabilities(notification_options=NotificationOptions(), experimental_capabilities={}),
        ))

if __name__ == "__main__":
    asyncio.run(main())
