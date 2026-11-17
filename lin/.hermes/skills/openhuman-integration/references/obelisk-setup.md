# Obelisk Build & Setup

Obelisk is a Rust binary at `/mnt/development1/obelisk/`.

## Build
```bash
cd /mnt/development1/obelisk
cargo build --release
install -m755 target/release/obelisk ~/.local/bin/obelisk
```

## Hermes Plugin
The plugin ships in the Obelisk repo at `plugins/hermes-obelisk/`. Install:
```bash
cp -R /mnt/development1/obelisk/plugins/hermes-obelisk ~/.hermes/plugins/obelisk
```

Then enable in config.yaml under `plugins.enabled`.

## Health Check
```bash
obelisk doctor
```
Should report healthy ledger (SQLite reversible store).

## Tools Registered
- `obelisk_run` — run a command and emit compact, reversible output
- `obelisk_pack` — build token-budgeted context bundle
- `obelisk_outline` — show file structure without dumping full file
- `obelisk_symbol` — read one symbol definition
- `obelisk_stats` — show token savings across layers
