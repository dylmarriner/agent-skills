# Worked Example: 99% Full → 51G Free in One Session

**Date**: 2026-04-30  
**Drive**: 219G root (dev/sdc3), secondary DEVELOPMENT1 at /media/kubuntux/DEVELOPMENT1 (220G, 41% used)

## Starting State

```
/dev/sdc3  219G  205G  2.6G  99% /
```

## Targets Found & Action Taken

### TIER 1 — Caches & Temp (direct delete, ~25G total)

| Target | Size | Action |
|--------|------|--------|
| /tmp | 3.9G | `sudo rm -rf /tmp/*` |
| ~/.local/share/Trash | 895M | `rm -rf ~/.local/share/Trash/*` |
| ~/.npm/_cacache | 4.3G | `rm -rf ~/.npm/_cacache/*` |
| ~/.npm/_npx | 984M | `rm -rf ~/.npm/_npx/*` |
| ~/.gradle/caches | 4.9G | `rm -rf ~/.gradle/caches/*` |
| ~/.cache | 4.0G | `rm -rf ~/.cache/*` |
| ~/.local/share/pnpm/store | 894M | `rm -rf ~/.local/share/pnpm/store/*` |
| ~/go/pkg/mod | 1.3G | `rm -rf ~/go/pkg/mod/*` |
| ~/.codeium | 1.1G | `rm -rf ~/.codeium/*` |
| ~/.openclaw.pre-migration | 58M | `rm -rf ~/.openclaw.pre-migration` |
| ~/.local/share/claude/* | 234M | `rm -rf ~/.local/share/claude/*` |
| ~/.local/share/opencode/* | 216M | `rm -rf ~/.local/share/opencode/*` |
| ~/.local/share/kilo/* | 596M | `rm -rf ~/.local/share/kilo/*` |
| ~/.local/share/GitKrakenCLI/* | 62M | `rm -rf ~/.local/share/GitKrakenCLI/*` |
| Chrome OptGuideOnDeviceModel | 4.0G | `rm -rf ~/.config/google-chrome/OptGuideOnDeviceModel/*` |
| journalctl + /var/log | 755M+ | `sudo journalctl --vacuum-size=200M` + find/delete |

### TIER 2 — Ask & Nuke (~12G total)

| Target | Size | Action |
|--------|------|--------|
| ~/.lmstudio | 2.3G | User said "I don't use lm studio" → `rm -rf ~/.lmstudio` |
| ~/.local/lib/python3.13 nvidia+torch | 7.4G | User confirmed no local ML → removed nvidia/ torch/ triton/ + ML libs |
| ~/.amp | 243M | Direct delete |
| ~/Downloads/IDA installers | 860M | Direct delete |
| ~/Downloads/tor-browser / linkr-zip | 240M | Direct delete |
| ~/lib/oracle-cli | 661M | `rm -rf ~/lib` |
| ~/.bun/install/cache | 200M | Direct delete |
| ~/.node-llama-cpp/models | 314M | Direct delete |

### TIER 4 — Moved to DEVELOPMENT1 (~10G total)

All moved to `/media/kubuntux/DEVELOPMENT1/old-docs/`:

| Project | Size |
|---------|------|
| Documents/Maer-Ken | 1.6G |
| Documents/Maer-Ken-1 | 2.1G |
| Documents/Cline | 2.9G |
| archive | 932M |
| llama.cpp | 790M |
| Documents/ATLAS-GATE-MCP | 439M |
| Documents/ATLAS-GATE-HOOKS | 100M |
| Documents/windsurf-hooker | 79M |
| Documents/robbie | 44M |
| Documents/shared-memory-mcp | 100M |
| Documents/ollama | 730M |
| Documents/messenger-downloader | 20K |
| Documents/empire-ai | 28K |
| Documents/llm-server | 264K |
| Documents/universal-unlock-suite | 1.2M |
| workspace | 144K |

### TIER 3 — Kept (explicitly preserved)

- Android Studio (6.3G) — user explicitly said keep
- Android SDK (2.4G)
- Ollama system models (20G at /usr/share/ollama/.ollama/models)
- Ollama user models (2.8G at ~/.ollama)
- All snap packages (7.2G) — Firefox, CUPS, core22/24, snapd, mesa
- Hermes (4.4G) — active agent
- Kiro CLI — actively used
- Chrome profile + config
- Windsurf / Antigravity config (not extensions)

## End State

```
/dev/sdc3  219G  157G  51G  76% /
```

## Key Lessons

1. **Always ask how aggressive** — "delete everything" usually means "aggressive but keep my tools and projects"
2. **Offer "move to secondary drive"** — user preferred this over deletion for large projects
3. **Categorize before presenting** — users respond better to a table than a firehose of file paths
4. **NDCU doesn't work in non-TTY** — use `du` and `find` directly instead
5. **Python ML libs are huge** — nvidia CUDA + torch alone can be 7G+. Confirm they're unused before removing.
6. **Check snap packages before suggesting removal** — `snap list` shows what's installed; Firefox, CUPS, mesa are system-critical
