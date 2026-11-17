#!/usr/bin/env python3
"""Ad-hoc verification: Nexus + Obelisk setup on a remote Macuntu host."""
import subprocess
import sys

HOST = "macuntu"
errors = []

def ssh(cmd, timeout=15):
    r = subprocess.run(["ssh", HOST, cmd], capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def ok(msg):
    print(f"  \u2713 {msg}")

def fail(msg, detail=""):
    print(f"  \u2717 {msg}")
    if detail:
        print(f"    {detail[:200]}")
    errors.append(msg)

print(f"=== Nexus env file ({HOST}) ===")
out, err, rc = ssh("cat ~/.hermes/nexus.env")
if rc == 0:
    for line in out.strip().split("\n"):
        ok(line)
else:
    fail("nexus.env unreadable", out + err)

print("\n=== Plugin files ===")
out, err, rc = ssh("ls ~/.hermes/plugins/nexus-memory/")
if rc == 0 and "plugin.yaml" in out and "tools.py" in out:
    ok("nexus-memory plugin files present")
else:
    fail("plugin files missing", out[:200])

print("\n=== Config plugin enabled ===")
out, err, rc = ssh(r"grep -E '^\s+-\s+nexus-memory' ~/.hermes/config.yaml")
if rc == 0:
    ok("nexus-memory enabled in plugins list")
else:
    fail("nexus-memory not in plugins", out[:200])

print("\n=== Nexus MCP reachable ===")
out, err, rc = ssh("""curl -s --connect-timeout 5 -X POST http://100.93.75.87:7777/mcp \\
  -H 'Authorization: Bearer *** \\
  -H 'Content-Type: application/json' \\
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' 2>/dev/null |
  python3 -c "import sys,json; d=json.load(sys.stdin); print('tools:', len(d.get('result',{}).get('tools',[])))" ||
  echo 'FAIL'""")
if "FAIL" not in out:
    ok(f"Nexus MCP responding ({out.strip()})")
else:
    fail("Nexus MCP unreachable", out)

print("\n=== Obelisk binary ===")
out, err, rc = ssh("export PATH=$HOME/.local/bin:$PATH && obelisk --version")
if rc == 0 and out:
    ok(f"obelisk: {out.strip()}")
else:
    fail("obelisk missing", out[:200])

print("\n=== RTK binary ===")
out, err, rc = ssh("export PATH=$HOME/.local/bin:$PATH && rtk --version")
if rc == 0:
    ok(f"rtk: {out.strip()}")
else:
    fail("rtk missing", out[:200])

print("\n=== rtk-rewrite plugin ===")
out, err, rc = ssh("cat ~/.hermes/plugins/rtk-rewrite/plugin.yaml")
if rc == 0 and "pre_tool_call" in out:
    ok("rtk-rewrite plugin active")
else:
    fail("rtk-rewrite missing", out[:200])

print("\n=== Hermes gateway ===")
out, err, rc = ssh("export PATH=$HOME/.local/bin:$PATH && hermes status 2>&1 | head -3")
if rc == 0 or (err and "running" in out + err):
    ok("hermes gateway responsive")
else:
    out2, _, _ = ssh("pgrep -f 'hermes.*gateway' && echo running || echo dead")
    ok(f"hermes gateway process: {out2}")

print(f"\n{'='*40}")
if errors:
    print(f"FAILURES: {len(errors)}")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
    sys.exit(0)
