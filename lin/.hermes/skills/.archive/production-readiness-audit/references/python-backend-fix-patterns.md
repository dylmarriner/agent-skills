# Python Backend Fix Patterns

Concrete before/after patterns for the most common Python backend production
issues found during audits. These are the lessons from an actual audit of
a Flask-based unlock suite — each pattern was found, diagnosed, and fixed
in a single session.

## Secrets in Source

**BAD** — hardcoded fallback key:
```python
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "") or "sk-REDACTED"
```

**GOOD** — env var only, no fallback:
```python
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
```

Also make all other config env-controllable:
```python
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
DEFAULT_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
AI_REQUEST_TIMEOUT = int(os.environ.get("AI_REQUEST_TIMEOUT", "60"))
```

## shell=True → shell=False

**BAD** — shell=True with string interpolation:
```python
subprocess.run(f'adb shell am start -a android.intent.action.DIAL -d tel:{code}',
               shell=True, timeout=10)
```

**GOOD** — argument list, no shell:
```python
_ADB_BASE = ["adb", "shell"]

def _adb(args: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(
        _ADB_BASE + args,
        capture_output=True, text=True, timeout=timeout
    )

_adb(["am", "start", "-a", "android.intent.action.DIAL", "-d", f"tel:{code}"], timeout=10)
```

Also replace `subprocess.run("cmd | grep X", shell=True)` with Python-level filtering
on `r.stdout`.

## Bare except: → Specific Exception

**BAD** — catches KeyboardInterrupt:
```python
try:
    return json.loads(result)
except:
    return default_value
```

**GOOD** — catches only what you expect:
```python
try:
    return json.loads(result)
except json.JSONDecodeError:
    return default_value
```

For subprocess calls:
```python
try:
    r = subprocess.run([...], timeout=10)
except subprocess.TimeoutExpired:
    logger.warning("Command timed out")
    return False
except Exception as e:
    logger.warning("Command failed: %s", e)
    return False
```

## Error Leakage to Client

**BAD** — `str(e)` sent to HTTP response:
```python
except Exception as e:
    return jsonify({'status': 'error', 'message': str(e)})
```

**GOOD** — generic message, stack trace in logs:
```python
except Exception as e:
    logger.exception("Unlock operation failed")
    return jsonify({'status': 'error', 'message': 'Unlock operation failed'})
```

Use `logger.exception()` inside exception handlers — it automatically includes
the full traceback.

## Hardcoded User Paths

**BAD** — only works on one machine:
```python
CRAWL_DIR = "/home/kubuntux/.openclaw/workspace/unlock_tools/crawl_results"
LIBRE_HACKTIVATOR_PATH = "/home/kubuntux/.openclaw/workspace/unlock_tools/LIBRE-HACKTIVATOR"
```

**GOOD** — env var with sensible fallback:
```python
CRAWL_DIR = os.environ.get(
    "CRAWL_RESULTS_DIR",
    os.path.expanduser("~/.unlock_tools/crawl_results")
)
LIBRE_HACKTIVATOR_PATH = os.environ.get(
    "LIBRE_HACKTIVATOR_PATH",
    os.path.expanduser("~/.unlock_tools/LIBRE-HACKTIVATOR")
)
```

## Deferred Import → Module Level

**BAD** — import hidden inside method body:
```python
def _call_deepseek(self, ...):
    try:
        import requests  # ← deferred
        ...
    except Exception:
        pass
```

**GOOD** — module-level import:
```python
import requests  # top of file

def _call_deepseek(self, ...):
    ...
```

If an import is genuinely optional (e.g. AI module that may not be installed),
wrap the MODULE-LEVEL import in a try/except, not a function body.

## Permissive CORS

**BAD** — accepts any origin:
```python
CORS(app)
```

**GOOD** — scoped origins:
```python
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:5000")
CORS(app, origins=CORS_ORIGINS.split(","))
```

## Debug Mode Default

**BAD** — Werkzeug debugger enabled by default:
```python
debug = os.environ.get('DEBUG', 'true').lower() == 'true'
```

**GOOD** — off by default:
```python
debug = os.environ.get('DEBUG', 'false').lower() == 'true'
```

(Failing to fix this exposes the `/console` Werkzeug debugger in production.)

## Thread-Unsafe Singleton

**BAD** — two threads can both pass the `is None` check:
```python
_ai_instance = None
def get_ai():
    global _ai_instance
    if _ai_instance is None:
        _ai_instance = UnlockAI()
    return _ai_instance
```

**GOOD** — module-level init is import-time-safe in CPython (GIL ensures atomicity):
```python
_ai_instance = None  # or just: _ai_instance = UnlockAI()

def get_ai():
    global _ai_instance
    if _ai_instance is None:
        _ai_instance = UnlockAI()
    return _ai_instance
```

For higher safety under eventlet/gevent: use `import threading; _lock = threading.Lock()`.

## Docker Compose Hardening

**BAD**:
```yaml
services:
  redis:
    image: redis:alpine
  unlock-backend:
    build: .
    environment:
      - FLASK_ENV=production
    depends_on:
      - redis
```

**GOOD**:
```yaml
services:
  redis:
    image: redis:7.4-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
    restart: unless-stopped

  unlock-backend:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - FLASK_ENV=production
      - JWT_SECRET=${JWT_SECRET}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:5000/api/health"]
      interval: 10s
      timeout: 5s
      retries: 6
    restart: unless-stopped
```

Key changes: version-pinned images, healthchecks with conditions, restart policy,
secrets via env vars (not build args), `depends_on: condition: service_healthy`.
