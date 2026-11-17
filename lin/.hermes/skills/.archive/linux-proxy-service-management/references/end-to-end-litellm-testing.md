# End-to-End Litellm Proxy Testing

Comprehensive test suite for validating a running Litellm proxy after setup or configuration changes. Run all tests — don't stop after the first pass.

## Prerequisites
- Litellm systemd service is `active` and `enabled`
- `Linger=yes` for user (systemd user services survive logout)
- Proxy port is accessible (default 4000)

## Test Suite

### 1. Systemd Health
```bash
systemctl --user is-active litellm-vertex.service   # → active
systemctl --user is-enabled litellm-vertex.service   # → enabled
loginctl show-user $(whoami) | grep Linger           # → Linger=yes
```

### 2. Litellm CLI Integrity
```bash
litellm --version
```
Must work without ImportError. If it hits linuxbrew Python 3.14 with missing deps, fix `.bashrc` PATH order so `~/.local/bin` comes after all `brew shellenv` calls.

### 3. Models Endpoint
```bash
curl -s -w "\nHTTP:%{http_code}" http://localhost:4000/v1/models \
  -H "Authorization: Bearer <master_key>"
```
Expected: HTTP 200, JSON array with configured model names.

### 4. Chat Completion
```bash
curl -s -w "\nHTTP:%{http_code}" http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer <master_key>" \
  -H "Content-Type: application/json" \
  -d '{"model":"<model_name>","messages":[{"role":"user","content":"Say OK"}],"max_tokens":100}'
```
Expected: HTTP 200, valid completion response. For Gemini 2.5 Flash, most tokens may be reasoning tokens — this is normal.

### 5. OpenCode Integration
```bash
opencode run "Reply with only: OK" --model <provider/model> --print-logs 2>/dev/null
```
- `--print-logs` is REQUIRED for the `run` subcommand to work in non-interactive/scripted mode (OpenCode v1.4.3 quirk)
- `2>/dev/null` discards verbose logging stderr
- Expected: model response on stdout, exit code 0
- If `--print-logs` is omitted, the command shows help text and exits code 1

### 6. Journal Check
```bash
journalctl --user -u litellm-vertex.service --since "5 minutes ago" -p warning --no-pager
journalctl --user -u litellm-vertex.service --since "5 minutes ago" -p err --no-pager
```
Expected: "No entries" for both.

## OpenCode-Specific Notes

### Provider Config (opencode.json)
```json
{
  "provider": {
    "vertex": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Vertex AI via LiteLLM",
      "options": {
        "baseURL": "http://localhost:4000/v1",
        "apiKey": "<master_key>"
      },
      "models": {
        "gemini-2.5-flash": { "name": "Gemini 2.5 Flash" }
      }
    }
  },
  "model": "vertex/gemini-2.5-flash"
}
```

### Known Issues
- **Duplicate skill warnings**: OpenCode v1.4.3 reports skills as "duplicate" with identical existing/duplicate paths. Cosmetic only — doesn't affect functionality. Use `--pure` to skip all skills/plugins and suppress these warnings entirely.
- **`run` subcommand**: Requires `--print-logs` in non-interactive terminal mode. Without it, shows help text and exits 1.
- **Gemini 2.5 Flash thinking tokens**: This model uses many reasoning tokens internally. A `max_tokens=50` completion may return `finish_reason: "length"` because 44 of 50 tokens were thinking. Increase `max_tokens` for substantive responses.
