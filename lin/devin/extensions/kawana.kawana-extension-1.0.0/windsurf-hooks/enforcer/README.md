# WindSurf Enforcer

A fail-closed, deterministic policy layer preventing incomplete code constructs across generation events.

## Features

- **Multi-language support**: Python, JavaScript, TypeScript, Java, C#, C++, Go, Rust, PHP, Swift
- **Dual validation**: Regex patterns + optional AST-based structural checks
- **Fail-closed security**: Unknown configurations block by default
- **Deterministic**: Same code always produces same result
- **Auditable**: JSONL logging of all validation attempts
- **No external dependencies**: Works offline; no network required

## Quick Start

### Development (Local)

```bash
cd windsurf-hooks/enforcer
python3 -m pip install pyyaml tree_sitter tree_sitter_languages

# Test the enforcer
echo '{"event":"post_generate","tier":"enterprise","language":"python","inputs":[{"path":"/tmp/test.py","content":"def foo():\n    raise NotImplementedError"}]}' | \
  PYTHONPATH=. python3 hooks/post_generate.py
```

### System Installation

See [INSTALL.md](INSTALL.md) for detailed setup instructions.

## Architecture

```
enforcer/
  ├── bin/
  │   └── windsurf-enforce          # Main executable wrapper
  ├── hooks/
  │   ├── pre_generate.py           # Pre-generation hook
  │   └── post_generate.py          # Post-generation hook
  ├── git-hooks/
  │   └── pre-commit                # Git pre-commit hook
  ├── etc/windsurf/enforcer/
  │   ├── policy.yaml               # Global policy configuration
  │   ├── tiers/                    # Tier definitions (strict, enterprise, defense-grade)
  │   └── languages/                # Language-specific rules (10+ languages)
  └── *.py                          # Core validation modules
      ├── config_loader.py
      ├── patterns.py
      ├── ast_engine.py
      └── validator.py
```

## Enforcement Rules

### Blocked Constructs

All languages block:

1. **Incomplete markers**
   - `// TODO`, `# FIXME`, `/* XXX */`, etc.

2. **Explicit errors**
   - Python: `raise NotImplementedError`
   - JavaScript/TypeScript: `throw new Error("Not implemented")`
   - Go: `panic("Not implemented")`
   - Rust: `todo!()`, `unimplemented!()`
   - etc. (language-specific)

3. **Structural placeholders** (AST, when enabled)
   - Empty function bodies: `{}`
   - Empty method bodies: `{}`

4. **Return value placeholders** (language-specific)
   - Python: `return None` (standalone)
   - JavaScript: `return null` (standalone)
   - Go: `return 0`, `return ""`, `return false`, `return nil`
   - etc.

### Example: Python

**Blocked:**
```python
def compute_checksum(data: bytes) -> str:
    raise NotImplementedError
```

**Allowed:**
```python
import hashlib

def compute_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
```

## Configuration

### Tiers

- **strict**: Regex only; fast, no AST required
- **enterprise**: Regex + optional AST (recommended)
- **defense-grade**: Regex + required AST; strictest

### Policy Format

```yaml
tier: enterprise
ast:
  enabled: true
  require_parsers: false
regex:
  enabled: true
threshold:
  max_violations: 0
```

### Language-Specific Rules

Add or modify rules in `languages/<lang>.yaml`:

```yaml
regex_rules:
  - id: py.custom
    description: custom incomplete marker
    pattern: '(?i)\bWIP\b'

structural_rules:
  - id: py.empty_function
    kind: empty_function_body
```

## API

### Input JSON (stdin)

```json
{
  "event": "pre_generate|post_generate",
  "tier": "strict|enterprise|defense-grade",
  "language": "python|javascript|...",
  "inputs": [
    {
      "path": "/abs/path/file.py",
      "content": "optional inline source"
    }
  ]
}
```

### Output JSON (stdout)

```json
{
  "allowed": true|false,
  "report": {
    "event": "post_generate",
    "tier": "enterprise",
    "language": "python",
    "results": [
      {
        "path": "/path/file.py",
        "hash": "sha256...",
        "violations": [
          {
            "rule_id": "py.not_implemented",
            "description": "explicit unimplemented exception",
            "start": 42,
            "end": 67,
            "excerpt": "raise NotImplementedError"
          }
        ]
      }
    ],
    "ts": 1234567890
  }
}
```

### Exit Codes

- **0**: Enforcement allowed; no violations
- **2**: Enforcement blocked; violations or configuration error

## Testing

```bash
cd tests
python3 -m pytest test_enforcer.py -v

# Or run specific test
python3 -m pytest test_enforcer.py::TestPythonEnforcement::test_not_implemented_blocked -v
```

## Integration

### WindSurf Hooks

Configure WindSurf to call:

```json
{
  "pre_write": [
    {
      "command": "windsurf-enforce post",
      "stdin": "json"
    }
  ]
}
```

### Git Hooks

Install pre-commit hook:

```bash
install -m 0755 enforcer/git-hooks/pre-commit .git/hooks/
export WINDSURF_TIER=enterprise
git commit  # Will block incomplete constructs
```

### CI/CD (GitHub Actions)

```yaml
- name: Enforce code completeness
  run: |
    python3 -m pip install pyyaml tree_sitter tree_sitter_languages
    python3 enforce-check.py --tier defense-grade
```

## Logging

Validation results logged to `/var/log/windsurf/enforcer.jsonl` (configurable):

```json
{"event":"post_generate","tier":"enterprise","allowed":false,"results":[...],"ts":1234567890}
```

## Performance

- **Regex matching**: ~1-2ms per file
- **AST parsing** (optional): ~10-50ms per file, language-dependent
- **No I/O overhead**: Pure in-memory validation

## License

See repository LICENSE file.

## Contributing

Report issues or suggest rules via repository issues.
