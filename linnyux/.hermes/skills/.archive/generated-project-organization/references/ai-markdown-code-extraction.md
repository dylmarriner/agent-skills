# AI Markdown Code Extraction

Extracting Python code from AI-generated markdown documents (DeepSeek, Claude, ChatGPT chat responses formatted as `.md` files). Unlike workspace export files, these documents have clean code fences but suffer from **markdown escape artifacts** and often need supporting-module scaffolding.

## The Source Format

AI chat exports typically wrap code in standard markdown fences:

```markdown
### 1. Xyz Engine — Production Ready (`path/to/file.py`)

```python
#!/usr/bin/env python3
"""Docstring"""
import os
```

### 2. Next Section
```

The code is syntactically valid Python from the AI's perspective, but the markdown processor may have **doubled every escape character**, producing these artifacts after the model sees it:

| Source (AI output) | Markdown-rendered artifact | Fixed |
|---|---|---|
| `\_` | `\\_` | `_` |
| `\\n` | `\\\\n` | `\n` |
| `\-` | `\\-` | `-` |
| `\\*` | `\\\\*` | `*` |

These happen because the AI wrote the code with ASCII backslashes, the markdown export escaped them for display, and what you read back has doubled backslashes everywhere.

## Workflow

### 1. Scope the Document

Use `read_file` with offset/limit to survey the document structure. AI markdown docs are often 2000-5000+ lines. Look for section headers (`### N. Module Name`):

```python
# Read the first 50 lines to understand structure
read_file(path="chat.md", limit=50)

# Then jump to each section
read_file(path="chat.md", offset=501, limit=500)
```

### 2. Identify All Code Sections

Note every section that contains a code block. The doc may also have:
- A **database schema** in SQL
- **Config JSON** inline
- **Dockerfile/docker-compose** snippets
- **Requirements.txt** lists

### 3. Extract via Parallel Subagents

For documents with 3+ code sections, dispatch `delegate_task` subagents in parallel (max 3 concurrent). Each subagent:

1. Reads the source file at its section offset
2. Extracts text between ```python (or ```sql, ```bash) and the closing ```
3. **Fixes markdown escape artifacts** — this is the critical step:
   - `\\_` → `_` (underscores in Python identifiers)
   - `\\\\n` → `\\n` (newlines in f-strings)
   - `\\-` → `-` (minus signs, hyphens)
   - `\\>` → `>` (greater than, dict annotations →)
   - `\\*` → `*` (multiplication, unpacking)
4. Removes language label line if present (e.g., the "python" right after ```)
5. Writes to the correct output path

### 4. Create Project Structure

After extraction, the project needs:
- `__init__.py` files for each package directory
- **Supporting modules** for dependencies the code references but the document didn't provide:
  - `rate_limiter.py` — if API routes import a DistributedRateLimiter
  - `circuit_breaker.py` — if resilience patterns are referenced
  - `gateway.py` — if an API Gateway class is imported
  - `architecture.py` — if enterprise event store/analytics are imported
- A `requirements.txt` pinned to compatible versions
- A `config.json` with the expected configuration shape
- `Dockerfile` + `docker-compose.yml` if the doc describes Docker services

### 5. Fix Compatibility Issues

AI-generated code often uses deprecated or broken libraries:

- **`aioredis`** — broken on Python 3.11+ (duplicate `TimeoutError` base class). Replace with `import redis.asyncio as aioredis` using a try/except fallback.
- **`pycryptodome`** vs **`cryptography`** — some code uses both. Keep both if explicitly imported, but `cryptography` is the modern standard.
- **`asyncpg.create_pool()`** called per-function — the AI writes a new pool per function call. This works but is inefficient. Acceptable for extraction fidelity; flag as optimization opportunity.

### 6. Verify with Behavioral Tests

AI-generated code passes `py_compile` but often has runtime bugs. Write a verification script that tests:

- **All modules import** — use `importlib.util.find_spec`
- **Sync methods execute correctly** — e.g. prefix matching, encoding roundtrips, accuracy calculations
- **Data structures are sound** — e.g. cell tower databases decode correctly
- **State machines behave** — rate limiter denies after N requests, circuit breaker opens after M failures
- **Roundtrip correctness** — encode → decode produces original input (catches nibble-order bugs)

## Bugs Found in Extracted AI Code

### TBCD Nibble Order

SS7/MAP code encodes phone numbers in TBCD format (3GPP TS 29.002). The AI-generated decoder typically outputs high nibble first, but TBCD stores the **odd-position digit** (first of each pair) in the **low nibble**. Correct decoder:

```python
# TBCD byte: low nibble = odd-positioned digit (first), high nibble = even (second)
d_odd = byte & 0x0F
d_even = (byte >> 4) & 0x0F
# Output: first digit then second digit
number += str(d_odd) + str(d_even)
```

### Packet/Protocol Field Width

AI-generated struct packing is often wrong for protocol headers. Always verify struct sizes match the spec (`struct.calcsize`).

### Missing Module-Level Imports

The AI's code may use `import aioredis` inside a function body without a module-level import, or reference `redis_client` as a module global that was never initialized. Fix by adding the import at the top.

## Handling Very Large Conversation Files (700K+)

Some conversation exports are enormous (19,000+ lines, 700K+). A sequential read-file approach is impractical. Use a **search-first strategy**:

### 1. Search for Code Block Markers

Open the file with `search_files` (or grep) to find all code fence locations:

```
search_files(path="conversation.md", pattern="```python")
search_files(path="conversation.md", pattern="```bash")
search_files(path="conversation.md", pattern="def class|class ")
```

This gives you every code block's line number in seconds instead of scrolling through 19K lines.

### 2. Search for Key Imports

Identify REAL vs simulated code by searching for actual library usage:

```
search_files(path="conversation.md", pattern="import usb")
search_files(path="conversation.md", pattern="import serial")
```

Simulated code rarely uses real hardware libraries. If you find `import usb.core`, that section is likely more grounded than sections that only do `time.sleep()` and print statements.

### 3. Search for Class/Function Definitions

```
search_files(path="conversation.md", pattern="class.*EDL|class.*Exploit")
search_files(path="conversation.md", pattern="def force_edl|def bypass_frp")
```

This lets you map the code landscape before reading any of it.

### 4. Read Only the Relevant Sections

Once you've identified which line ranges contain real-looking code, read only those sections with `read_file(offset=N, limit=M)`. Batch independent reads in parallel.

## Handling Multiple Code Iterations from Same Conversation

Long conversations often produce 10-30+ code blocks across multiple assistant turns. Not all iterations are equal:

### Iteration Quality Gradient

| Turn Position | Typical Quality | Signal |
|---|---|---|
| Early (1st-2nd) | Simulated / skiddie | `time.sleep` as logic, fake hex dumps, "This would interface with..." comments |
| Middle (3rd-7th) | Intermediate | Real imports (`usb.core`, `struct`), proper classes, but still placeholder methods |
| Late (8th+) | Production-grade | Proper error handling, logging, type hints, multiple methods with fallback chains |
| Final "warroom/pwn" iterations | Maximally aggressive | Cuts through bullshit — short, direct, real ADB/USB commands, no decorative prints |

### Synthesis Strategy

Don't just take the last iteration. **Synthesize across iterations:**

1. **Structure from the best-organized iteration** — look for the one with proper module separation, clear class hierarchy, and docstrings
2. **USB communication patterns from iterations with `pyusb`** — the `usb.core.find()`, `ctrl_transfer()`, `bulk_write()` patterns are usually consistent
3. **ADB/fastboot command strings from the warroom iterations** — the "real fucking exploit" sections often have the most accurate shell commands
4. **FRP partition paths from device-specific iterations** — verify these against known Android partition layouts
5. **Error handling and logging from late iterations** — early ones use bare `print()`, later ones use proper `logging.getLogger`

## Identifying Real vs Simulated Code Within Conversations

Conversations with jailbreak/godmode/persona-switching prompts (e.g., "[START OUTPUT} ... GODMODE: ENABLED ... LOVE PLINY") often contain mixed-quality outputs.

### Red Flags for Simulated Code

- Comments like `# This would normally interface with libusb/pyusb` — the author is admitting they don't actually call pyusb
- `print("[+] SUCCESS")` with no preceding real operation
- `time.sleep(2)` as the only "processing" between mock responses
- `return True` unconditionally after a try block with no actual work
- **Bogus hex payloads** passed to fake functions — e.g., `b'\\xFE\\xED\\xFA\\xCE'` that look cool but have no real protocol meaning
- **Non-existent VID/PIDs** — VID 0x0e8d is real MediaTek; but a made-up PID like 0xDEAD is not
- **Persistence/backdoor code** — shell scripts that listen on nc ports, C2 commands, init.d scripts — these are ideological payloads, not EDL exploit code
- **ROP chains with fake addresses** — addresses like `0x100070`, `0xA0000000` pulled from nowhere
- **"For educational purposes" disclaimers combined with no actual exploit mechanism**

### Green Flags for Real Code

- `import usb.core` and actual `usb.core.find()` calls
- `import struct` with real `struct.pack` / `struct.unpack` for protocol messages
- `subprocess.run()` with actual ADB/fastboot commands
- Multiple method fallback chains (try A, then B, then C)
- Device VID/PID constants matching real hardware (0x05C6=Qualcomm, 0x0E8D=MediaTek, 0x18D1=Google fastboot)
- Partition paths matching real Android block device layout
- Comments that acknowledge limitations ("requires root", "only works on unlocked bootloader")

## Integrating Extracted Code Into Existing Projects

When the output goes into an existing project rather than creating a new one:

1. **Follow existing conventions** — Check the project's `__init__.py` exports, logging style (bare `print()` vs `logging.getLogger`), error return types (`bool` vs `ExploitResult` dataclass), and docstring format
2. **Respect the existing project hierarchy** — Don't create new top-level directories; place files where they logically belong
3. **Update or verify `__init__.py`** — Ensure the new module's public API is exported matching the old contract (if upgrading an existing file)
4. **Match existing import patterns** — If the project uses `from .edl_forcer import EDLForcer`, keep that convention. If it uses relative imports, use relative imports
5. **Don't break the parent package** — If the parent `__init__.py` imports modules with missing dependencies (e.g., `cryptography`, outdated pyusb), test your module independently, not through the broken chain

## Pitfalls

- **30-second SS7 connection timeout** — ProductionSS7Engine's `__init__` tries to connect to carrier gateways. These timeout (5s each × 6 gateways = 30s). Accept this for testing or refactor `__init__` to not block on connection in tests.
- **`uv pip install` vs system pip** — On PEP 668 systems, use `uv pip install` rather than `pip install`. Some packages (pyaudio, opencv) need `apt` system deps first.
- **No `numpy` in slim containers** — opencv-python-headless pulls numpy, which needs a compiler on Alpine/slim. Use `python:3.12-slim` base and install `libgomp1`.
- **Doc may claim "production ready" but have pass bodies** — Scan every function for bare `pass`, `NotImplementedError`, or `time.sleep` as the only logic. These are simulation patterns, not production code.
- **Section ordering can be ascrambled** — Some AI exports reorder sections or interleave code with unrelated commentary. Read the section header, not the position, to identify what each block contains.
