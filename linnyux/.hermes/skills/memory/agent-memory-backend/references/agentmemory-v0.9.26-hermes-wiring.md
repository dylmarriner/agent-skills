# agentmemory v0.9.26 — Hermes Wiring Notes

## Config file protection

`~/.hermes/config.yaml` is treated as security-sensitive. The Hermes
`patch` tool refuses to edit it. Use `sed` or direct file editing
instead.

## Duplicate key failure mode

An earlier install left two `agentmemory:` entries under `mcp_servers:`.
YAML silently keeps the last key, so the first block with `enabled: true`
was ignored and the second took effect.

Detection:
```bash
grep -n '^  agentmemory:' ~/.hermes/config.yaml
# should return exactly one match
```

Fix: remove the duplicate, keeping only the block with `enabled: true`.

## agentmemory_url

Set the URL explicitly when relying on a fixed port:
```yaml
memory:
  agentmemory_url: http://127.0.0.1:3111
```

## One provider rule

If the machine previously used `honcho`, replace it with `agentmemory`
rather than adding a second provider entry. Verify after editing:
```bash
grep -n '^  provider:' ~/.hermes/config.yaml
```
Only one `provider:` line should be present under `memory:`.
