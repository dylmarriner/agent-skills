# Placeholder Detection Patterns

Reference catalog of code patterns that indicate simulated/placeholder behavior in AI-generated prototype code.

## HIGH Severity — Simulation Code

### 1. time.sleep() Processing

```python
# BAD: prints step names and sleeps instead of actually doing work
print("[1/5] Reconnaissance...")
time.sleep(1)
print("[2/5] SS7 Exploitation...")
time.sleep(1)
```

Detection: `time.sleep(N)` where N > 0.3 and the surrounding function has no real I/O or network calls.

### 2. Static Mock Returns

```python
# BAD: returns hardcoded success without any actual operation
def deploy_attack(target):
    return {
        "status": "compromised",
        "target": target,
        "carrier": "Spark NZ",
        "surveillance_port": 8443
    }
```

Detection: `return {"status": "..."}` — especially `compromised`, `success`, `deployed`, `active`.

### 3. NotImplementedError Stubs

```python
# BAD: function exists but does nothing
def intercept_sms(self):
    raise NotImplementedError("SMS interception not implemented")
```

Detection: `raise NotImplementedError` anywhere in function body.

## MEDIUM Severity — Unfinished Code

### 4. pass Bodies

```python
# BAD: empty function body
def complex_operation(self):
    pass
```

Detection: `def ...():` followed by indented `pass`, especially in large classes.

### 5. TODO/FIXME Comments

```python
# TODO: implement actual exploit logic
# FIXME: this doesn't work on production
# HACK: temporary workaround
```

### 6. Generic Exceptions

```python
# BAD: no specific error type
raise Exception("Something went wrong")
```

## LOW Severity — Placeholder Data

### 7. RFC1918 Private IPs

| Range | Common Use |
|-------|------------|
| `10.x.x.x` | Carrier SS7 gateways, internal infrastructure |
| `192.168.x.x` | Local network addresses |
| `172.16-31.x.x` | Docker/Kubernetes networks |

Detection: IP addresses from these ranges in config JSON/YAML or Python string literals.

### 8. Hardcoded Credentials

```python
API_KEY = "sk-test-1234"
DB_PASSWORD = "password123"  # placeholder
```

### 9. Placeholder Comments

```python
# For demonstration purposes only
# Simulate the attack chain
# In production, this would...
```

## Combined Verdict Categories

| Verdict | Criteria |
|---------|----------|
| Working prototype | Real socket/network/API calls, valid logic, no sleep-based simulation |
| Skeleton with fake logic | Structure is complete but every function uses sleep() or static returns |
| Half-functional | Some real code (Flask routes, scapy packets) but core logic is placeholder |
| Decorative only | Scripts that just print progress bars, no real side effects |

## File-Level Assessment

When auditing, check each file for:
1. **Real tech used** — flask routes, scapy, socket I/O, subprocess, cryptography, DB queries
2. **Sleep count** — functions that only print+sleep are simulation
3. **Static returns** — hardcoded dicts pretending to be from real ops
4. **Dead imports** — references to modules that don't exist (`backend.exploits.*` etc.)
5. **Script real ops** — shell scripts that actually run sudo/apt/docker vs just `echo`
