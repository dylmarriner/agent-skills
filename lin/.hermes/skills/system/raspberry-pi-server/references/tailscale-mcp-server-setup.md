# Tailscale MCP Server — ACL Modification from Blocked Nodes

The [HexSleeves/tailscale-mcp-server](https://github.com/HexSleeves/tailscale-mcp-server) is a Bun-based MCP server that wraps Tailscale's REST API. It can read and modify ACL rules, letting you unblock your own SSH access from the same node that's currently blocked.

## When to Use

- Tailscale SSH returns: `tailnet policy does not permit you to SSH to this node`
- You have (or can get) a Tailscale API key or OAuth client credentials
- You want to fix the ACL and SSH in, rather than writing a handoff script
- This machine (your current node) is tagged `tag:infra` — common for CI/agent machines that ACLs restrict

## Prerequisites

- **Bun 1.3+** — `curl -fsSL https://bun.sh/install | bash`
- **Tailscale API access** — one of:
  - API key: generated from https://login.tailscale.com/admin/settings/keys
  - OAuth client: created at https://login.tailscale.com/admin/settings/oauth with scopes `devices_core:write`, `policy:write`

## Setup: stdio Mode (for MCP clients)

```json
{
  "mcpServers": {
    "tailscale": {
      "command": "bunx",
      "args": ["@hexsleeves/tailscale-mcp-server"],
      "env": {
        "TAILSCALE_API_KEY": "tskey-api-...",
        "TAILSCALE_TAILNET": "-"
      }
    }
  }
}
```

Or with OAuth:

```json
{
  "mcpServers": {
    "tailscale": {
      "command": "bunx",
      "args": ["@hexsleeves/tailscale-mcp-server"],
      "env": {
        "TAILSCALE_OAUTH_CLIENT_ID": "...",
        "TAILSCALE_OAUTH_CLIENT_SECRET": "...",
        "TAILSCALE_TAILNET": "-"
      }
    }
  }
}
```

## Setup: HTTP Mode (standalone service)

```bash
export MCP_TRANSPORT=http
export MCP_HTTP_BEARER_TOKEN="$(openssl rand -base64 32)"
export TAILSCALE_API_KEY="tskey-api-..."
export TAILSCALE_TAILNET="-"
bunx @hexsleeves/tailscale-mcp-server
# Listens on http://127.0.0.1:3000 with bearer auth
```

## Risk Levels

| Level | What You Can Do |
|-------|-----------------|
| `read` | List devices, inspect status, read ACL/diagnostics (default) |
| `write` | Update ACLs, DNS, routes, policy files, tags |
| `admin` | Delete/deauthorize devices, manage auth keys, destructive ops |

Set via `TAILSCALE_ALLOWED_TOOL_RISK` env var. For ACL fixes, you need **`write`**.

## ACL Modification — Key Tools

### `manage_acl` (write risk)

Reads and writes the tailnet ACL policy file (HUJSON format). The ACL has an `ssh` array of rules.

### `list_devices` (read risk)

Shows all devices on the tailnet with their tags, IPs, and online status. Essential to find the target device ID before tagging or ACL changes.

### `manage_device_tags` (admin risk)

Changes a device's tags. Required when you need to add a tag to the target device so SSH rules can reference it.

## SSH Rule Syntax — What Actually Works

Tailscale SSH rules have strict `dst` limitations that differ from ACL rules. **This is the most common source of errors.**

### Valid `dst` values for SSH rules

| Value | Works? | Notes |
|-------|--------|-------|
| `autogroup:self` | ✅ | Users can SSH to their own devices. Default rule. |
| `tag:<name>` | ✅ | SSH to all devices with that tag. Requires tag to exist in `tagOwners`. |
| `autogroup:member` | ❌ | Returns `invalid dst "autogroup:member"` |
| `*` | ❌ | Returns `invalid dst "*"` |
| `user@domain.com` | ❌ | Returns `users in dst are only allowed from the same user` |
| `*:*` | ❌ | Invalid format for SSH rules |

### The only working pattern for cross-user SSH

To allow `tag:infra` to SSH into devices owned by another user, you **must tag the target device** and use that tag as `dst`:

```
1. Create tag in tagOwners:      tag:pi → ["user@domain.com"]
2. Apply tag to target device:   device → tag:pi
3. Add SSH rule:                src: [tag:infra], dst: [tag:pi]
```

### Step-by-step: Direct API (no MCP server needed)

You can do all of this with curl and the Tailscale REST API. This is often faster than setting up the MCP server:

```bash
# 0. Set your API key
API_KEY="tskey-api-..."

# 1. Get current ACL
curl -s -H "Authorization: Bearer $API_KEY" \
  "https://api.tailscale.com/api/v2/tailnet/-/acl" > /tmp/current-acl.json

# 2. Get device list (find target device ID)
curl -s -H "Authorization: Bearer $API_KEY" \
  "https://api.tailscale.com/api/v2/tailnet/-/devices" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'{x[\"name\"]}: {x[\"id\"]} tags={x.get(\"tags\",[])}') for x in d['devices']]"

# 3. Modify the ACL (add tagOwners + SSH rule)
python3 << 'PYEOF' | curl -s -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d @- \
  "https://api.tailscale.com/api/v2/tailnet/-/acl"
import json, re, sys

# Load current ACL (may be HUJSON with trailing commas)
with open('/tmp/current-acl.json') as f:
    raw = f.read()

# Strip trailing commas for JSON parsing
fixed = re.sub(r',\s*([}\]])', r'\1', raw)
acl = json.loads(fixed)

# Add tag to tagOwners
acl.setdefault('tagOwners', {})['tag:pi'] = ['user@domain.com']

# Add SSH rule (must use tag in dst, NOT autogroup:member)
acl.setdefault('ssh', []).insert(0, {
    "src": ["tag:infra"],
    "dst": ["tag:pi"],
    "users": ["autogroup:nonroot", "root"],
    "action": "accept",
})

print(json.dumps(acl, indent="\t"))
PYEOF

# 4. Tag the target device
curl -s -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tags": ["tag:pi"]}' \
  "https://api.tailscale.com/api/v2/device/<device-id>/tags"

# 5. Verify — should now work
ssh <user>@<target-tailscale-ip> "hostname"
```

### Common ACL Patterns

### Grant infra-tagged machines SSH to tagged devices

```json
{
  "action": "accept",
  "src": ["tag:infra"],
  "dst": ["tag:pi"],
  "users": ["autogroup:nonroot", "root"]
}
```

Requires `tag:pi` in `tagOwners` and applied to the target device.

### Gotcha: ACL change is not enough — device needs `--ssh` flag

Adding a tag and ACL rule does NOT enable Tailscale SSH on the target device. The device must also have the Tailscale SSH feature enabled:

```bash
# On the target device
sudo tailscale up --ssh

# Or verify it's already enabled
tailscale status --json | grep -o '"SSHEnabled":true'
```

If `SSHEnabled` is false on the target device, no ACL rule will work. No error is returned — SSH just silently fails. Always check this before debugging ACL syntax.

- **API key vs OAuth scoping**: An API key inherits the permissions of the user who created it. If that user is a tailnet admin, the key has full access. An OAuth client needs explicit scopes (`policy:write`, `devices_core:write`) granted in the admin console.
- **ACL propagation delay**: ACL changes take 5-30 seconds to propagate to all nodes. Don't assume it failed after one try — wait and retry.
- **Risk level limits tool access**: With `TAILSCALE_ALLOWED_TOOL_RISK=read`, `manage_acl` returns an error. Set it to `write`.
- **HUJSON format**: Tailscale ACLs use Human JSON (HUJSON), which supports comments. The MCP server handles the format conversion. Use `manage_acl` to read the current policy, modify it, and write it back.
- **Don't break existing rules**: Always read the current ACL first with `manage_acl`, make your change, then write back. If you overwrite the ACL with only your new rule, you'll break all other access policies.
- **autogroup:member vs tag**: `autogroup:member` matches all user-owned devices. Tags like `tag:infra` match devices that have that tag. A rule with `src: ["tag:infra"]` and `dst: ["autogroup:member"]` allows any infra-tagged device to reach any user-owned device.
- **`autogroup:member` is not in `dst` by default**: Many tailnets only have `tag:*` based rules in dst. If you add `autogroup:member`, check you're not allowing unintended access.
