# WindSurf Enforcer Installation Guide

## Local Development Setup

### Prerequisites

- Python 3.9+
- pip
- bash
- git (for hook integration)

### Install Dependencies

```bash
python3 -m pip install --upgrade pyyaml tree_sitter tree_sitter_languages
```

### Verify Installation

```bash
cd windsurf-hooks/enforcer
./bin/windsurf-enforce post < /dev/null  # Should return JSON error
```

Expected output:
```json
{"allowed":false,"error":"empty_input"}
```

---

## System-Wide Installation (Linux)

### Create Required Directories

```bash
sudo install -d /etc/windsurf/enforcer/languages /etc/windsurf/enforcer/tiers
sudo install -d /usr/local/lib/windsurf/enforcer/hooks
sudo install -d /usr/local/bin /usr/local/share/windsurf/enforcer/git-hooks
sudo install -d /var/log/windsurf
```

### Install Python Modules

```bash
sudo cp -r windsurf-hooks/enforcer/windsurf_hooks /usr/local/lib/windsurf/
sudo cp -r windsurf-hooks/enforcer/etc/windsurf/enforcer /etc/windsurf/
```

Or install as an editable package:

```bash
cd windsurf-hooks/enforcer
sudo python3 -m pip install -e .
```

### Install Executables

```bash
sudo install -m 0755 windsurf-hooks/enforcer/bin/windsurf-enforce /usr/local/bin/
sudo install -m 0755 windsurf-hooks/enforcer/hooks/pre_generate.py /usr/local/lib/windsurf/enforcer/hooks/
sudo install -m 0755 windsurf-hooks/enforcer/hooks/post_generate.py /usr/local/lib/windsurf/enforcer/hooks/
```

### Install Git Hook

```bash
# For this repository
install -m 0755 windsurf-hooks/enforcer/git-hooks/pre-commit .git/hooks/pre-commit

# Or globally (if configured)
install -m 0755 windsurf-hooks/enforcer/git-hooks/pre-commit /usr/local/share/windsurf/enforcer/git-hooks/
```

### Verify Installation

```bash
windsurf-enforce post < /dev/null
# Should output JSON error
```

---

## Docker Setup

If using Docker, include in your Dockerfile:

```dockerfile
RUN python3 -m pip install pyyaml tree_sitter tree_sitter_languages
COPY windsurf-hooks/enforcer /usr/local/lib/windsurf/enforcer
COPY windsurf-hooks/enforcer/bin/windsurf-enforce /usr/local/bin/
RUN chmod 0755 /usr/local/bin/windsurf-enforce
```

---

## Configuration

### Global Policy (`/etc/windsurf/enforcer/policy.yaml`)

Main enforcement configuration. Defines:
- Logging path
- Behavior (fail-closed, max input size)
- Language registry
- Tier definitions

### Tiers

- **strict**: Regex only, fail on any violation
- **enterprise**: Regex + AST (best effort), fail on violations
- **defense-grade**: Regex + AST (required), fail on violations or parser unavailability

### Language-Specific Rules

Located in `languages/*.yaml`. Each file defines:
- File extensions
- Regex rules (comment markers, error throws, etc.)
- Structural rules (empty functions/methods via AST)

---

## Usage

### Hook Invocation

#### Pre-generation (WindSurf integration)

```bash
echo '{"event":"pre_generate","tier":"enterprise","language":"python","inputs":[{"path":"src/example.py"}]}' | windsurf-enforce pre
```

#### Post-generation (file validation)

```bash
echo '{"event":"post_generate","tier":"enterprise","language":"typescript","inputs":[{"path":"src/api.ts","content":"function parse() { throw new Error(\"Not implemented\"); }"}]}' | windsurf-enforce post
```

### Git Hook

Automatically runs on `git commit` to block incomplete constructs:

```bash
export WINDSURF_TIER=enterprise
git commit -m "Add feature"  # Will block if violations detected
```

---

## Troubleshooting

### ImportError: No module named 'tree_sitter'

```bash
python3 -m pip install tree_sitter tree_sitter_languages
```

### ConfigError: missing_config

Ensure policy.yaml exists at the expected location:
- `/etc/windsurf/enforcer/policy.yaml` (system)
- `./etc/windsurf/enforcer/policy.yaml` (relative to module)

### Exit code 2 but no error in stdout

Check stderr:
```bash
echo '...' | windsurf-enforce post 2>&1
```

### Hook not running

Verify executable permissions:
```bash
ls -la .git/hooks/pre-commit
chmod 0755 .git/hooks/pre-commit
```

---

## Testing

Run the test suite:

```bash
cd tests
python3 -m pytest test_enforcer.py -v
```

Expected output: All tests pass (assume tree_sitter optional for enterprise tier)

---

## Security Notes

1. **Fail-closed**: If configuration is unreadable, enforcement blocks.
2. **No network**: Pure local validation; safe for offline environments.
3. **Read-only config**: Policy files are never modified.
4. **Audit trail**: All validation attempts logged to `/var/log/windsurf/enforcer.jsonl`.

---

## Advanced: Custom Rules

To add a language or extend rules, modify `languages/*.yaml`:

```yaml
language: mylan
file_extensions: [".ml"]

regex_rules:
  - id: ml.custom_marker
    description: custom incomplete construct
    pattern: 'failwith "not implemented"'

structural_rules:
  - id: ml.empty_function
    kind: empty_function_body
```

Reload is automatic; no service restart required.
