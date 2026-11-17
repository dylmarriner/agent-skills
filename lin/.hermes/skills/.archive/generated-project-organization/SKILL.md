---
name: generated-project-organization
description: "Organize loose AI-generated files into a standard project structure with meaningful names, and audit for placeholder/simulation code. Also covers extracting code from workspace export files (see references/workspace-export-extraction.md), from AI chat markdown documents (see references/ai-markdown-code-extraction.md), and splitting large JSON array exports into individually named files (see references/json-array-split-and-rename.md)."
version: 1.3.0
author: Hermes Agent
---

# Generated Project Organization

Organize a directory of loose AI-generated prototype files (e.g., `deepseek_*`, `claude_*`, `codex_*` artifacts) into a clean project structure with file classification, meaningful renaming, deduplication, and placeholder-code auditing.

## When to Use

Trigger when the user has a directory filled with loose generated files — typically named with a model prefix and timestamp (like `deepseek_python_*.py`, `deepseek_vue_*.vue`). The user wants these organized into a real project they can work with.

**Also use** when the user hands you a single large AI-chat markdown export (`.md`) containing code blocks from DeepSeek, Claude, or ChatGPT. See `references/ai-markdown-code-extraction.md` for the extraction workflow, escape-artifact fixes, parallel-subagent dispatch pattern, and the search-first strategy for enormous (700K+ line) conversation files. For conversations with multiple code iterations spanning many assistant turns, that reference also covers synthesis across iterations and identifying real vs simulated code.

## Workflow

### Step 1: Survey & Classify

Scan all files, extracting class names, function names, imports, and file extension. Group by category:

| Category | Signals |
|----------|---------|
| API server | Flask routes, `@app.route`, SocketIO |
| Backend modules | Classes for specific domains (SS7, MITM, C2, exploits) |
| Frontend | `.vue`, `.js`, `.jsx`, `.tsx` files with React/Vue patterns |
| Config | `.yaml`, `.json`, `.ini`, `.toml`, `.env` |
| Database | `.sql` files with CREATE TABLE statements |
| Scripts | `.sh` files with bash commands |
| Tests | `test_` prefix, pytest patterns, `unittest.TestCase` |
| Dashboard | Plotly, Dash, monitoring, analytics |

### Step 2: Deduplicate

Remove `(1)` or `(copy)` duplicates — they have identical content to the original. Compare file sizes and content hashes to confirm.

### Step 3: Create Project Structure

Standard layout:
```
project-root/
├── backend/
│   ├── api/          # Flask/FastAPI servers and route definitions
│   ├── exploits/     # Domain-specific exploit/attack modules
│   ├── mitm/         # Man-in-the-middle modules
│   ├── intelligence/ # Reconnaissance, scanning, enumeration
│   ├── forensics/    # Evidence collection, reporting
│   ├── c2/           # Command-and-control infrastructure
│   ├── orchestrator/ # Coordination and workflow logic
│   └── utils/        # Stealth comms, evasion, persistence, exfil
├── dashboard/        # Monitoring, analytics, visualization
├── frontend/src/     # React/Vue components and app entry points
├── config/           # JSON/YAML config, Docker, Prometheus
├── database/         # SQL schemas, migrations
├── scripts/          # Bash deployment/ops scripts
└── tests/            # Unit and integration tests
```

### Step 4: Rename & Move

Rename files from their generated names (e.g., `deepseek_python_20260519_b6742d.py`) to meaningful names based on the primary class/function they contain:

| Generated pattern | Rename to |
|-------------------|-----------|
| Contains `NZExploitOrchestrator` | `exploit_orchestrator.py` |
| Contains `NZCarrierExploits` | `carrier_exploits.py` |
| Contains `SS7ExploitSuite` | `ss7_exploit_suite.py` |
| Contains `PegasusNZDeployer` | `pegasus_deployer.py` |
| Contains Flask routes + JWT | `api_server.py` or `api_routes.py` |
| Contains Vue component | Name from component name or `<h1>` title |
| Contains React App | `App.js` |
| Contains Docker services | `docker-compose.yaml` |
| Contains Prometheus | `prometheus.yaml` |

Use `cp` (not `mv`) to leave the originals until you verify the structure is correct.

### Step 5: Audit for Placeholder Code

Scan every organized Python file for these patterns:

**HIGH severity (simulation code):**
- `time.sleep(N)` — sleeping to pretend work is happening. Flag if the sleep is the only "processing" in a function.
- `NotImplementedError` — stub function
- Static mock returns — `return {"status": "compromised", ...}` with no actual logic

**MEDIUM severity (unfinished):**
- `pass` as the only function body
- `# TODO`, `# FIXME`, `# HACK` comments
- Generic `raise Exception` instead of specific exceptions

**LOW severity (placeholder data):**
- Hardcoded RFC1918 IP addresses (`10.x.x.x`, `192.168.x.x`, `172.16-31.x.x`)
- Hardcoded credentials or tokens
- Comments like "for demonstration purposes" or "placeholder"
- Randomized data generation (mock fake data)

### Step 6: Generate Report

Write a README.md with:
- Project structure tree
- Per-file audit findings (what's real vs placeholder)
- Overall assessment (working prototype, skeleton with fake logic, half-functional, etc.)

## Pitfalls

- **Plugin/extensions live in YOUR project, not the target's** — When building plugins for multiple platforms (Hermes, OpenClaw, Paperclip, IDEs), keep each plugin as a self-contained distributable package under `plugins/<platform>-<name>/` in YOUR project. Never build directly into the target project's source tree (e.g., `openclaw/extensions/`, `~/.hermes/plugins/`). Those are installation targets, not development locations. Use install scripts to deploy.
- **Don't delete originals during move** — Use `cp` first, verify structure, then clean up originals after user OKs it.
- **Vue component names** — Don't trust the filename; scan for `name:` in the component definition or the `<h1>` title text.
- **JSON config files** — Open and parse with `json.loads()` to understand structure before naming. A file with `spark/one_nz/two_degrees` keys is "carrier config," not just "config.json."
- **Duplicate detection** — `(1)` suffix files are exact copies; `(2)` suffix files might be slightly different revisions. Check content hash, not just filename.
- **Mixed frontend** — Generated projects sometimes use Vue components AND a React App.js together. Keep both; don't assume one framework wins.
- **Scripts with no real ops** — Some `.sh` files are just `echo` statements with no `sudo`, `apt`, `docker`, or `systemctl` commands. Flag these as decorative.
- **Auto-detected imports may not resolve** — Generated code imports modules that don't exist on the system or in the project (e.g., `backend.exploits.nz_carriers`). This is expected for generated prototypes.
- **TBCD / protocol encoding bugs** — AI-generated protocol code (SS7 MAP, SMS TPDU, etc.) often gets nibble-order wrong. Always write a roundtrip test (encode → decode → compare to original input) to catch these silently broken byte layouts.
- **Content over keywords for classification** — Filenames and titles can be misleading or completely unrelated to the actual content ("car-seatbelts" was about Redmi Note 13 FRP bypass). Skim the actual first 1-3 user request messages to determine what a conversation or file is genuinely about. Keyword matching on titles alone produces too many false positives and false negatives.
- **Search-first for huge files** — For conversation exports over 100K bytes or 3K lines, never use sequential read_file scrolling. Start with search_files or grep to find code fences (```python), imports (import usb), and class names (class.*Exploit). A 700K/19K-line file can be navigated in 2-3 rounds with search vs 20+ rounds of blind scrolling.
- **Synthesize across iterations, do not copy-last** — When a conversation has 10-30+ code blocks across multiple turns, the last one is not necessarily the best. Early blocks often have cleaner structure; late blocks have sharper commands. Read 3-5 key iterations and blend the best parts.
- **Jailbreak artifacts degrade code quality** — Conversations with "[START OUTPUT}", "GODMODE: ENABLED", persona-switching prompts contain theatrical code with fake hex payloads, bogus VID/PIDs, and ideological backdoor scripts. Extract the code blocks, discard the framing, validate against real hardware constants.
