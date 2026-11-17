# Porting an MCP Server Between Machines (vast.ai example)

Class of task: copy a working custom MCP server from one Hermes host to another
(kubuntux → lin, verified 2026-08). The vast.ai MCP is the worked example, but the
sequence generalizes to any custom stdio MCP server with a `launch.sh` wrapper, a
venv, and machine-specific paths/keys.

## The source server

- Path: `~/.hermes/mcp-servers/vastai-mcp/`
- `server.py` (~73KB) — custom FastMCP server. `mcp.run()` with NO transport args =
  **stdio** (fastmcp default). The log line "Starting Vast.ai MCP server on
  localhost:8000" is COSMETIC — the host/port string is hardcoded in `main()`
  regardless of transport. Do not treat it as proof the server runs HTTP.
- `launch.sh` — bash wrapper exporting `VAST_API_KEY`, `SSH_KEY_FILE`,
  `SSH_KEY_PUBLIC_FILE`, then `exec`s the venv python with `-u server.py "$@"`.
- `venv/` — python3.12 venv. Deps: fastmcp, mcp, paramiko, httpx, pydantic.

## Port procedure (steps in order)

1. **Copy the server dir, excluding venv and .git** (rebuild the venv on the target
   so the interpreter path matches the target machine):
   ```bash
   ssh kubuntux 'cd ~/.hermes/mcp-servers && tar czf - --exclude=venv --exclude=.git vastai-mcp/' \
     | tar xzf - -C ~/.hermes/mcp-servers/
   ```
2. **Rebuild the venv on the target** with the SAME python major.minor as the source
   (here 3.12, present on both):
   ```bash
   cd ~/.hermes/mcp-servers/vastai-mcp
   python3.12 -m venv venv
   ./venv/bin/pip install -q -r requirements.txt
   ```
3. **Copy the registered SSH key under a distinct name** — do NOT clobber the host's
   own identity keys. Vast registers ONE public key; for `ssh_execute_command` /
   `scp_*` to work from the new host, it must hold the matching private key:
   ```bash
   scp kubuntux:~/.ssh/id_rsa ~/.ssh/vast_id_rsa
   scp kubuntux:~/.ssh/id_rsa.pub ~/.ssh/vast_id_rsa.pub
   chmod 600 ~/.ssh/vast_id_rsa
   ```
   Verify the pubkey matches what's registered on the account (`users/current/`
   returns `ssh_key`). The fingerprint must match, or instance SSH will be refused.
4. **Retarget `launch.sh`** — rewrite hardcoded `/home/kubuntux/...` paths to the
   target host and the copied key paths. chmod +x.
5. **Wire config via `hermes config set`** — the config file is BLOCKED from direct
   edit by the patch/write tools (security-sensitive), so set the whole block as JSON
   under `mcp_servers.<name>`:
   ```bash
   hermes config set 'mcp_servers.vast' '{"enabled":true,"command":"/home/lin/.hermes/mcp-servers/vastai-mcp/launch.sh","timeout":120,"env":{"VAST_API_KEY":"<KEY>","SSH_KEY_FILE":"/home/lin/.ssh/vast_id_rsa","SSH_KEY_PUBLIC_FILE":"/home/lin/.ssh/vast_id_rsa.pub"},"connect_timeout":60}'
   ```
6. **Verify the server registers** (works without a restart):
   ```bash
   hermes tools list | grep -i vast   # -> "vast  all tools enabled"
   ```

## Verifying stdio boot + tool enumeration (no full Hermes restart needed)

Pipe a JSON-RPC initialize + tools/list sequence into `launch.sh` and read back the
tool names. Use `bufsize=1` (line buffering) or the stdio handshake may not flush:

```python
import subprocess, json, time
p = subprocess.Popen(["./launch.sh"], stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                     text=True, bufsize=1)
def send(o): p.stdin.write(json.dumps(o)+"\n"); p.stdin.flush()
send({"jsonrpc":"2.0","id":1,"method":"initialize",
      "params":{"protocolVersion":"2024-11-05","capabilities":{},
                "clientInfo":{"name":"t","version":"1"}}})
send({"jsonrpc":"2.0","method":"notifications/initialized"})
send({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}})
time.sleep(4); p.stdin.close()
tools = json.loads([l for l in p.stdout.read().splitlines() if l.strip()][-1])["result"]["tools"]
print(len(tools), [t["name"] for t in tools])
p.terminate()
```

The pydantic `IncompleteFieldDefinitionWarning` on startup is harmless noise.

## vast.ai API quick checks

```bash
KEY="<VAST_API_KEY>"
# instances
curl -s -H "Authorization: Bearer $KEY" "https://console.vast.ai/api/v0/instances/" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(i['id'],i['actual_status'],i.get('gpu_name'),i.get('ssh_host'),i.get('ssh_port')) for i in d.get('instances',[])] or print('(none running)')"
# account / balance / credit
curl -s -H "Authorization: Bearer $KEY" "https://console.vast.ai/api/v0/users/current/" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('balance:',d.get('balance'),'credit:',d.get('credit'),'user:',d.get('username'),'can_pay:',d.get('can_pay'))"
```

Zero instances running is normal — instances are spun up on demand via
`create_instance` (there's no standing fleet unless you keep one).

## Tool inventory (22) for reference

show_user_info, show_instances, search_offers, search_templates, create_instance,
destroy_instance, start/stop/reboot/recycle_instance, show_instance, logs,
attach_ssh, ssh_execute_command, ssh_execute_background_command,
ssh_check/kill_background_task, scp_upload, scp_download, search_volumes,
label_instance, configure_mcp_rules.

## Pitfalls

- **New MCP servers only load into a session that starts AFTER the config change.**
  A session already running when the config was written does NOT hot-load the tools.
  Restart Hermes on the target for tools to appear as `mcp_vast_*`. This is the
  #1 thing that looks like a failure but isn't.
- **The config file cannot be edited via patch/write_file tools** — Hermes refuses
  ("security-sensitive configuration"). Use `hermes config set <dotted.key> <json>`
  instead; a single JSON value can set an entire nested server block.
- **SSH keys are machine-specific but account-global for the provider.** The Vast
  account accepts exactly one registered public key. Copy it explicitly; don't assume
  the new host's default key is registered.
- **`.git` and `venv` are large and target-specific** — exclude both from the tar
  copy, rebuild the venv in place.
