---
name: dark-web-to-code-pipeline
description: "Targeted dark web research → organized exploit module creation → application API integration"
version: 1.0.0
author: Hermes
tags: [dark-web, tor, osint, exploit-development, frp, android, security]
---

# Dark Web → Code Pipeline

End-to-end workflow for doing targeted dark web research, extracting findings, creating organized exploit modules, and integrating them into an application's API.

## When to Use

- User asks to "crawl the dark web" for a specific topic (e.g. Samsung FRP, iCloud bypass, MDM removal)
- User asks to integrate dark web findings into an existing application
- Building exploit modules from research documentation
- Creating organized exploit manager hierarchies

## Phase 1: Assessment

Before starting, check what already exists:

```bash
# Check existing crawl infrastructure
ls ~/.unlock_tools/crawl_results/ 2>/dev/null
ssh root@<crawl-host> "ls ~/.openclaw/workspace/unlock_tools/crawl_results/" 2>/dev/null

# Check Tor availability
which tor && systemctl is-active tor 2>/dev/null

# Check existing research docs
find . -name '*FRP*' -o -name '*BYPASS*' -o -name '*UNLOCK*' 2>/dev/null

# Check existing exploit module structure
find backend/exploits/ -name '*.py' | sort
```

## Phase 2: Dark Web Search

### Tor Proxy Setup
```python
import requests
session = requests.Session()
session.proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
```

### Search Engines to Try (in order)
1. **Ahmia** — `http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/search/?q={query}`
2. **Torch** — `http://xmh57jrknzkhv6y3ls3ubitzfqnkrwxhopf5aygthi7d6rplyvk3noyd.onion/cgi-bin/Lurker$/search?search_string={query}`
3. **DuckDuckGo** — `http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/html/?q={query}`
4. **Known forum/market crawls** — use existing findings.jsonl if a crawler daemon is running

**Pitfalls:**
- Most dark web search engines are unreliable — expect 50%+ failure rates
- **Real-world result from 8-minute deep search across 100+ onion sites:** ZERO useful results. Every onion search engine (Ahmia, Torch) returned nothing. DuckDuckGo Tor blocks automated HTML queries. Most .onion sites are dead or blocking Tor exit nodes.
- **GitHub surface repos are more productive than dark web for tool discovery.** The FRP bypass tools found in this session all came from GitHub (riskeco ⭐273, jodin3 ⭐113, EDL Loaders ⭐94, frp-freedom ⭐251), not dark web. Surface web Google results pointed to HalabTech repair firmware, SamFW tool, and XDA forums.
- **Practical strategy:** Search GitHub API first for tool discovery, then use dark web only for niche content (leaked firehose programmers, signed bootloaders, combination firmware). Even then, expect 90% failure rate.
- Always use `torsocks curl` as a fallback when Python requests fail
- Timeouts should be 30-45s minimum
- Crawl requests are slow (3-5s between requests minimum)
- Save every finding immediately to findings.jsonl

### Saving Findings
```python
import json
findings = []
with open("findings.jsonl", "a") as f:
    f.write(json.dumps({
        "timestamp": datetime.utcnow().isoformat(),
        "url": url,
        "source": source,
        "snippet": html[:3000] if html else "",
        "reachable": reachable,
        "tags": tags,
    }) + "\n")
```

## Phase 3: Exploit Module Architecture

### Directory Structure
```
backend/exploits/
├── android/
│   ├── __init__.py          # package
│   ├── adb/
│   │   ├── __init__.py      # re-export ADBExploitManager
│   │   └── exploits.py      # ADBExploitManager class
│   ├── interface/
│   │   ├── __init__.py      # re-export InterfaceExploitManager
│   │   └── exploits.py      # InterfaceExploitManager class
│   ├── system/
│   │   ├── __init__.py      # re-export SystemExploitManager
│   │   └── exploits.py      # SystemExploitManager class
│   └── hardware/
│       ├── __init__.py      # re-export HardwareExploitManager
│       └── exploits.py      # HardwareExploitManager class
└── core/
    └── frp_device_manager.py
```

### Manager Class Template
```python
class ExploitManager:
    def __init__(self, config: dict, device_manager=None):
        self.config = config
        self.device_manager = device_manager
        self.logger = logging.getLogger(f"{__name__}.ExploitManager")

    def execute_method(self, method_name, device_info, progress_callback=None):
        method_map = {
            "example_bypass": self.example_bypass,
        }
        handler = method_map.get(method_name)
        if not handler:
            return {"status": "error", "method": method_name, "results": f"Unknown method"}
        return handler(device_info, progress_callback)

    def example_bypass(self, device_info, progress_callback=None) -> Dict[str, Any]:
        try:
            # Implementation
            return {"status": "success", "method": "example_bypass", "results": {...}}
        except Exception as e:
            self.logger.exception("example_bypass failed")
            return {"status": "failed", "method": "example_bypass", "results": str(e)}
```

### Critical Rules
1. **ALL subprocess calls must use `shell=False`** with argument lists. Never `shell=True`.
2. Use a private helper for subprocess: `_adb(args, timeout)`, `_fastboot(args, timeout)`
3. **Every method returns `Dict[str, Any]`** with `status`, `method`, `results` keys
4. Use `logger.exception()` in except blocks, not `logger.error(f"...: {e}")`
5. Import `BypassResult` from project types module for status enums
6. Every `__init__.py` in exploit package: thin re-export from `exploits` module

## Phase 4: API Integration

### Add Methods to API Endpoints
The application's `BypassMethodsAPI` and `AIMethodSelectAPI` must list all available methods so the frontend and AI can reference them:

```python
# In BypassMethodsAPI.get():
methods.append({
    "name": "method_name",
    "category": "adb|system|hardware|interface|legacy",
    "risk": "low|medium|high",
    "android_versions": "11-16",
    "description": "Human readable description"
})
```

### Wire Into Pipeline
Update the dispatch in `UnlockAPI.post()` to route operation strings to the correct exploit manager:

```python
if 'android' in op_lower or 'frp' in op_lower:
    from backend.exploits.integrated_android import IntegratedAndroidExploitSuite
    aes = IntegratedAndroidExploitSuite()
    result = aes.execute_frp_bypass(model, android_ver)
```

## Phase 5: Samsung S24 Unlock Pipeline

For **locked Samsung devices with USB debugging disabled** (pattern/PIN/password-locked, no ADB), the software approach won't work. Use the Download Mode → Combination Firmware → ADB → Lock Clear pipeline.

### Pipeline Steps
1. Power off phone completely (hold Power + Volume Down for 7s)
2. Volume Down + Power → Download Mode (USB VID:PID = 04e8:685d)
3. Flash combination (engineering) firmware via Odin/Heimdall
4. Boot combo firmware → full ADB root access (no lock screen)
5. Pull & clear gatekeeper.db / locksettings.db / gatekeeper.*.key
6. Reboot → lock screen removed

### Combination Firmware
- File pattern: `COMBINATION_FA81_<MODEL>*.tar.md5`
- Model prefixes: SM-S921 (S24), SM-S926 (S24+), SM-S928 (S24 Ultra)
- Sources: SamFW, SamMobile, XDA forums
- Boots with `adb root` enabled, engineering kernel

### Lock Screen Data Files
- `/data/system_de/0/spgatekeeper.db` — Gatekeeper password hash
- `/data/system/locksettings.db` — Lock type and credential config
- `/data/system/gatekeeper.password.key` / `gatekeeper.pattern.key`
- `/data/system/device_policies.xml` — Failed attempt counter

### Clear Methods (in order)
1. **Delete gatekeeper keys**: `rm -f /data/system/gatekeeper.*.key`
2. **Edit locksettings.db**: `sqlite3 ... DELETE FROM locksettings WHERE name LIKE '%lock%'`
3. **Nuclear**: Delete ALL credential data

### Pitfalls
- Knox Vault stores credentials in hardware-isolated processor — combo firmware bypasses at bootloader level
- Combo firmware first boot takes 90-120 seconds
- S24 uses Snapdragon 8 Gen 3 — EDL firehose programmers are bootloader-authenticated
- `shell=True` prohibition is CRITICAL for subprocess — use command lists everywhere
- **PID 0x685d is shared across generations** — lsusb text "Galaxy S II" is a lie. Verify actual model via `adb devices` product string or model number from the user.

## Phase 5c: Recovery ADB Sideload Path (for MDM-locked Devices)

When the phone is MDM-enrolled (auto-re-locks during setup after factory reset), the download mode pipeline won't help. The MDM profile survives in the Knox-managed partition.

### Recovery Access
```bash
# From phone off: Volume Up + Power → recovery menu
# Navigate with Volume buttons. Select "Apply update from ADB"
```

### What ADB Sideload Mode Allows
```
$ adb devices
R5CW90M2ZQH  sideload  product:sm-a546e model:SM_A546E
```
- ✅ `adb sideload <ota.zip>` — flash an OTA update
- ✅ `adb reboot` / `adb reboot recovery` / `adb reboot download`
- ❌ No `adb shell`, `adb push`, `adb root`

### MDM Package Removal (requires full ADB, not sideload)
```bash
adb shell pm disable-user --user 0 com.samsung.android.kgclient
adb shell pm uninstall --user 0 com.samsung.android.kgclient
adb shell pm uninstall --user 0 com.samsung.android.mdm
adb shell pm disable-user --user 0 com.sec.enterprise.knox.cloudmdm.smdms
```

### Getting Full ADB from Recovery
1. Recovery → Wipe data/factory reset
2. Reboot → during boot, hold **Volume Down** until "Safe mode" appears
3. In safe mode, MDM policies don't load
4. Navigate to **Settings → About Phone → Software Info → Build Number** (tap 7×)
5. **Developer Options → USB Debugging → ON**
6. Now `adb shell` works and MDM packages can be removed

## Phase 5b: Production Hardening (Pre-Release)

After building exploit modules and before declaring them production-ready, run this audit:

### Critical Security Checks
1. **Hardcoded secrets** — grepping `sk-`, `your-`, `changeme` in all source files is mandatory
   ```bash
   grep -rn 'sk-[a-zA-Z0-9]\{20,\}\|your-secret\|changeme\|your_api' --include='*.py' --include='*.yaml' --include='*.json' .
   ```
2. **`shell=True`** in subprocess calls — every occurrence must be `shell=False` with argument lists
   ```bash
   grep -rn 'shell=True' --include='*.py' .
   ```
3. **CORS** — `CORS(app)` with no args accepts all origins. Must pin: `CORS(app, origins=os.environ.get("CORS_ORIGINS", "http://localhost:5000").split(","))`
4. **Debug mode** — `app.run(debug=True)` defaults Werkzeug debugger to ON (RCE risk). Default must be `False`:
   ```python
   debug = os.environ.get("DEBUG", "false").lower() == "true"
   ```
5. **Bare except:** — Replace with specific exception types. `except:` catches `KeyboardInterrupt` and `SystemExit`.
6. **Error message leakage** — `str(e)` in API responses leaks internals. Return generic messages to clients, log full details server-side.

### CORS Fix Pattern
```python
# BAD (allows any website to call the API):
CORS(app)

# GOOD (scoped to known origins):
CORS(app, origins=os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:5000"
).split(","))
```

### Error Handling Pattern
```python
# BAD (leaks internals, no stack trace):
except Exception as e:
    return jsonify({'message': str(e)})

# GOOD (logs full traceback, returns safe message):
except Exception as e:
    logger.exception("Operation failed: %s", e)
    return jsonify({'message': 'Operation failed'})
```

### Secret Management Pattern
```python
# BAD (hardcoded fallback):
API_KEY = os.environ.get("API_KEY", "") or "sk-4475e877bba94488..."

# GOOD (env var only, raises at startup if missing):
_JWT_SECRET = os.environ.get("JWT_SECRET", "")
if not _JWT_SECRET:
    raise RuntimeError("JWT_SECRET environment variable is required")
```

### Import Pattern
```python
# BAD (deferred import hides failures):
def handler():
    try:
        import requests
        ...
    except Exception:
        ...

# GOOD (module-level import with graceful fallback for optionals):
try:
    import requests
except ImportError:
    requests = None
```

## Phase 6: Nexus Feature Integration

When adding endpoints to Nexus (Postgres + asyncpg + SQLAlchemy):

### UUID Fix
- Raw SQL inserts need `gen_random_uuid()` for UUID primary keys
- Python-level `default=uuid.uuid4()` is NOT a database default
- Use `CREATE TABLE IF NOT EXISTS ... id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- Without `gen_random_uuid()` every INSERT fails: `NotNullViolationError: null value in column "id"`

### JSONB with asyncpg
- asyncpg cannot serialize Python lists/dicts to JSONB via bind parameters
- Use `json.dumps()` on list/dict before passing as parameter
- Use `CAST(:param AS jsonb)` in SQL (not `::param::jsonb` suffix — that causes `syntax error at or near ":"`)
- For `jsonb_build_object()`, construct the object in Python and pass as single param

### Metadata Serialization Pattern (BROKEN to FIXED)
```python
# BROKEN — jsonb_build_object with separate params fails:
jsonb_build_object('tags', :tags::jsonb, 'source', :source, 'kind', :kind)
# -> syntax error at or near ":"
# -> IndeterminateDatatypeError for parameter $N

# BROKEN — old params dict with separate keys, missing 'metadata':
{"tags": json.dumps(tag_list), "source": source, "kind": kind, ...}  # no "metadata" key
# -> "A value is required for bind parameter 'metadata'"

# FIXED — build full JSON in Python, pass as single CAST param:
metadata_val = json.dumps({
    "tags": tag_list,
    "source": source,
    "kind": kind,
    "title": title_str,
})
await db.execute(
    text("INSERT INTO memories (...) VALUES (CAST(:metadata AS jsonb), ...)"),
    {"metadata": metadata_val, ...},
)
```

### FastAPI Body Parsing
- Mixing path params with multiple body params confuses FastAPI (treats body as list)
- Use `body: dict` pattern for POST endpoints with complex input
- Extract fields via `body.get("key")`
- Example:
  ```python
  @router.post("/projects/{key}/remember")
  async def remember(key: str, body: dict, db: AsyncSession = Depends(get_db)):
      kind = body.get("kind", "note")
      limit = max(1, min(50, int(body.get("limit", 10))))
  ```

### Development Workflow (Docker)
- Add `volumes: - .:/app:ro` to docker-compose to skip image rebuilds
  ```yaml
  volumes:
    - .:/app:ro
  ```
- Clear `__pycache__` after code changes:
  ```bash
  find /app -name '__pycache__' -exec rm -rf {} + 2>/dev/null
  ```
- Restart only the changed service: `docker compose up -d <service>`
- Verify: `docker logs <service> --tail 5` and `curl /health`

### Testing New Routes
```bash
# Health first
curl -s /health | python3 -m json.tool

# Then test each new endpoint
curl -s -X POST /v1/synapse/projects/register?key=test \
  -H "Authorization: Bearer $SECRET" | python3 -m json.tool

# Check server logs on 500:
docker logs nexus-nexus-api-1 --tail 10

# Fix and restart cycle:
docker compose up -d nexus-api
sleep 8
curl -s /health
```

## User Preferences
- **Zero narration**: Do not explain what you're about to do or narrate steps
- **Just execute**: State the result in 2-3 lines. If it works, report what happened concisely
- **No apologies**: If something fails, state result and blocker — no explanations or apologies
- **No walls of text**: Skip itemized listings and verbose analysis

## Verification

```bash
# Verify all imports resolve
python3 -c "import sys; sys.path.insert(0, '.'); from backend.exploits.android.bypass_manager import BypassManager; print('OK')"

# Check no shell=True in exploit code
grep -rn "shell=True" backend/exploits/ 2>/dev/null

# Verify AST parses
python3 -c "import ast; ast.parse(open('backend/exploits/android/adb/exploits.py').read()); print('Syntax OK')"
```

## References
See `references/frp-bypass-methods-research.md` for the compiled FRP bypass research document.
See `references/samsung-frp-crawl-summary.md` for the dark web crawl results summary.
See `references/samsung-s24-unlock-pipeline.md` for the full S24 unlock pipeline details.
See `references/nexus-feature-integration-patterns.md` for Nexus synapse-compat integration patterns.
