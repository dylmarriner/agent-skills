# Wiring the vast.ai MCP server into Hermes on lin

Session-tested procedure (2026-08-23) for installing the custom vast.ai MCP server on a machine that already runs it on kubuntux. The server is a hand-built FastMCP server (~73KB `server.py`), not a pip package.

## The server
- Source: `~/.hermes/mcp-servers/vastai-mcp/` on kubuntux
- Files: `server.py` (FastMCP, 22 tools), `launch.sh` (env + venv exec), `wrapper.py`, `mcp_config.json`, `pyproject.toml`, `requirements.txt`, `test_mcp*.py`
- 22 tools: show_user_info, show_instances, search_offers, search_templates, create_instance, destroy/start/stop/reboot/recycle_instance, show_instance, logs, attach_ssh, ssh_execute_command, ssh_execute_background_command, ssh_check/kill_background_task, scp_upload, scp_download, search_volumes, label_instance, configure_mcp_rules

## Install steps
1. Copy the dir, excluding venv + .git (rebuild venv locally; both machines have python3.12):
   ```
   ssh kubuntux 'cd ~/.hermes/mcp-servers && tar czf - --exclude=venv --exclude=.git vastai-mcp/' \
     | tar xzf - -C ~/.hermes/mcp-servers/
   ```
2. Build venv: `python3.12 -m venv venv && ./venv/bin/pip install -r requirements.txt`
   Deps confirmed: fastmcp 3.4.7, mcp 1.29.0, httpx, httpx-sse, paramiko 5.0.0, pydantic, pydantic-settings.
3. Copy the SSH key that is REGISTERED on the vast account (kubuntux's `~/.ssh/id_rsa`) to `~/.ssh/vast_id_rsa` on lin — that registered pubkey is what allows SSH into rented instances. Two separate `scp` calls (one source → one dest each; multi-dest scp errors).
4. Rewrite `launch.sh` paths to the new machine (`/home/lin/...`, `SSH_KEY_FILE=/home/lin/.ssh/vast_id_rsa`).

## Smoke test (stdio)
FastMCP's `mcp.run()` with no args = stdio transport. The log line "Starting Vast.ai MCP server on localhost:8000" is COSMETIC — it prints regardless of transport; don't mistake it for an HTTP server.

Verify tools enumerate via a stdio handshake:
```python
import subprocess, json, time
p = subprocess.Popen(["./launch.sh"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
for m in [{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}},
          {"jsonrpc":"2.0","method":"notifications/initialized"},
          {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}]:
    p.stdin.write(json.dumps(m)+"\n"); p.stdin.flush()
time.sleep(4); p.stdin.close()
print([t["name"] for t in json.loads(p.stdout.read().splitlines()[-1])["result"]["tools"]])
p.terminate()
```
Expect 22 tool names.

## Register in Hermes config
The `patch`/`write_file` tools REFUSE `~/.hermes/config.yaml` (security-protected). Use the CLI with a dotted key + JSON value:
```
hermes config set 'mcp_servers.vast' '{"enabled":true,"command":"/home/lin/.hermes/mcp-servers/vastai-mcp/launch.sh","timeout":120,"env":{"VAST_API_KEY":"<KEY>","SSH_KEY_FILE":"/home/lin/.ssh/vast_id_rsa","SSH_KEY_PUBLIC_FILE":"/home/lin/.ssh/vast_id_rsa.pub"},"connect_timeout":60}'
```
Verify: `hermes tools list | grep -i vast` → "vast  all tools enabled". Check the block: `grep -A12 '^  vast:' ~/.hermes/config.yaml`.

Tools load only on a fresh session (or MCP reload notice). A session started before the config change won't have `mcp__vast__*` until restarted.

## MCP search tool quirk
`mcp__vast__search_offers` can 400 on some queries because the server hardcodes `allocated_storage: 5.0` into the query object. For reliable pricing, PUT directly to `https://console.vast.ai/api/v0/search/asks/` (see SKILL.md). If using the tool: query is space-separated `key=value`, order uses `field+` (asc) / `field-` (desc).
