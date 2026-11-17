---
name: sentinelx-deploy
description: Install or repair the SentinelX Ollama dashboard on Linux.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [sentinelx, ollama, flask, systemd, pentest, self-hosted]
    related_skills: [self-hosted-app-setup, linux-proxy-service-management]
---

# SentinelX deploy / repair

## When to Use

- Installing `github.com/cypher-21/SentinelX` (or redeploying it on another host).
- The dashboard returns a blank/error page, `/api/health` says `ollama:false`, or the model pill
  lists no models.
- `./run.sh` fails with "Address already in use" or leaves port 5000 held after Ctrl+C.
- Ollama reports `mkdir /usr/share/ollama: permission denied`, or `ollama` is missing from `$PATH`
  even though `/usr/local/lib/ollama` exists.

Flask dashboard (`sentinelx.server`, port 5000, `127.0.0.1`) + Ollama on `:11434`.
State lives in `~/.sentinelx/data.db` (per-user, so run it as the user, never root).

## Non-obvious pitfalls (all hit in the field)

- **The cloned `.venv` is often a corpse**: only `bin/python` symlinks, no `pip`, no `site-packages`
  (created with a Python that no longer matches). Always `rm -rf .venv && python3 -m venv .venv`
  then `.venv/bin/pip install -r requirements.txt`, and optionally `.venv/bin/pip install -e .`
  to get the `sentinelx` console script.
- **Ollama's binary can vanish while its libs remain**: `/usr/local/lib/ollama` exists but
  `/usr/local/bin/ollama` is gone, and `systemctl status ollama` is `inactive (dead)` with a stale
  unit. Fix = re-run `curl -fsSL https://ollama.com/install.sh | sh` (idempotent; restores the
  binary **and** rewrites `/etc/systemd/system/ollama.service`).
- **The installer does not create the service user's home**: `User=ollama` with
  `OLLAMA_MODELS=/usr/share/ollama/.ollama/models` fails with
  `mkdir /usr/share/ollama: permission denied`. Pre-create it:
  `sudo mkdir -p /usr/share/ollama/.ollama && sudo chown -R ollama:ollama /usr/share/ollama`.
- **A drop-in override survives the reinstall** but the unit file itself gets overwritten —
  re-check `/etc/systemd/system/ollama.service.d/override.conf` after install and keep
  `OLLAMA_VULKAN=1` / `GGML_VK_VISIBLE_DEVICES=0` for AMD (a Polaris RX 470/480/580 does
  ~26 tok/s on qwen2.5:7b Q4_K_M). Drop `OLLAMA_DEBUG=1` — it floods the journal.
- **`run.sh` kills port 5000 with `fuser -k`** on start and on exit, so it fights a systemd unit.
  Patch it to stop `sentinelx.service` first if active: `references/runsh-service-patch.md`.
- **Never judge run.sh shutdown by backgrounding it.** A bash started asynchronously has
  SIGINT/SIGQUIT set to SIG_IGN and POSIX forbids trapping them, so `trap cleanup INT` never
  fires and the Flask child is orphaned on port 5000. Test it only with a foreground terminal
  (or `timeout -s INT 15 bash ./run.sh`).

## Order of operations

```bash
# 1. Ollama present and running
curl -fsSL https://ollama.com/install.sh | sh
sudo mkdir -p /usr/share/ollama/.ollama && sudo chown -R ollama:ollama /usr/share/ollama
sudo systemctl daemon-reload && sudo systemctl enable --now ollama
curl -s http://localhost:11434/api/tags          # expect {"models":[...]}

# 2. Models (size to VRAM: 8 GB → 7B Q4 + 3B)
ollama pull qwen2.5:7b-instruct
ollama pull llama3.2:3b
cd <repo> && ollama create sentinelx -f ./models/Modelfile   # custom pentest-mentor persona
ollama list

# 3. App venv
rm -rf .venv && python3 -m venv .venv
.venv/bin/pip install -r requirements.txt && .venv/bin/pip install -e .

# 4. systemd --user unit so it survives logout, then enable linger
systemctl --user daemon-reload && systemctl --user enable --now sentinelx.service
sudo loginctl enable-linger $USER
```

Unit template: `references/sentinelx.service`. Do **not** put `After=ollama.service` in a
user unit — cross-scope ordering refs are dropped/noisy; Ollama is a system unit and is
independent anyway.

## Verify (real, not assumed)

```bash
curl -s http://127.0.0.1:5000/api/health              # ollama:true + models_count
SID=$(curl -s -X POST http://127.0.0.1:5000/api/sessions -H 'Content-Type: application/json' \
      -d '{"name":"verify","model":"sentinelx:latest"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["session_id"])')
curl -sN -X POST http://127.0.0.1:5000/api/chat/stream -H 'Content-Type: application/json' \
  -d "{\"message\":\"one line: what are you\",\"session_id\":\"$SID\",\"model\":\"sentinelx:latest\"}"
```

A healthy install streams text and writes 2 rows into `~/.sentinelx/data.db`. Finish with a
browser check of `http://127.0.0.1:5000` (dark UI, `sentinelx:latest` in the model pill).

Optional: `~/.local/share/applications/sentinelx.desktop` with `Exec=xdg-open http://127.0.0.1:5000`.
