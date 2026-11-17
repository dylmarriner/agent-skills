# Syncthing P2P Config Sync Across Tailscale Mesh

Preferred alternative to NFS shared profiles. Each machine keeps ~/.hermes/ fully local, Syncthing daemon keeps them in sync in real-time. No mount dependencies, no boot blocking, no single point of failure.

## Architecture

```
Lin ──────┬────── Macuntu
           │
      Syncthing (P2P)
           │
Kubuntux ──┴────── Rabuntu
```

Every machine peers with every other. Changes propagate to all. `.stignore` filters out runtime junk (sessions, logs, state.db, caches) — only actual config syncs.

## Device IDs Table

| Machine | Device ID |
|---------|-----------|
| lin | T2FBAYJ-THJ7M7B-LAYJ7N4-RDKCMRR-SFQWHK2-GM3WYLR-QEQBYOX-7JARJAA |
| macuntu | XUSOLHP-P6RPQCZ-76R6AHN-XUFIB5H-JIBCXTP-LOXLDX2-V3UWVAJ-6QGE5A5 |
| kubuntux | 6DVL55E-42ZUDTC-OS44MUT-5XGCWXM-BALYVP6-Y7WVWKJ-I6IPQAN-4EEV7A7 |
| rabuntu | N6FA6UH-FYQHPCZ-OPPI47Z-G5KLBML-MNO4YKN-RRSLKVN-HMMGW3D-7CRTVQH |

## Step-by-Step Setup

### 1. Install Syncthing

```bash
# Debian/Ubuntu
sudo apt-get install -y syncthing

# Already installed? Verify version
syncthing --version
```

### 2. Generate Initial Config & Get Device ID

```bash
# Generate cert + config
syncthing --generate=~/.local/state/syncthing

# Get device ID
syncthing --device-id
# Returns: XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXXA
```

**Pitfall:** `syncthing --device-id` reads from the existing cert. If no cert exists yet, it prints an error. Run `--generate` first.

### 3. Create .stignore in ~/.hermes/

Filter out machine-specific runtime data. Place this at `~/.hermes/.stignore`:

```
// Runtime data - machine specific
state.db*
state-snapshots/
checkpoints/
sessions/
sessions.local/
logs/
cache/
audio_cache/
image_cache/
sandboxes/
verification_evidence.db*

// Build artifacts
bin/
node_modules/
lsp/
hermes-agent/
__pycache__
*.pyc
*.pyo
*.egg-info

// Backups - huge tarballs
.curator_backups/
**/.curator_backups
*.bak
*.backup*
*nexus-backup*

// Hub caches
.hub/
**/.hub

// Codegraph
codegraph/

// Lock/process files
*.lock
gateway_state.json
gateway.pid
processes.json
channel_directory.json

// Large generated files
.skills_prompt_snapshot.json
*_cache.json
context_length_cache.yaml
interrupt_debug.log
daily-update.log
.hermes_history

// Honcho
honcho-venv/

// Temp
pastes/
whatsapp/
mcp-servers/
migration/
memory/
kanban.db*

// Standard skills from upstream - only local modified skills synced
skills/
```

**Key design decisions:**
- `skills/` is ignored — standard skills come from upstream (skills.sh, clawhub) and are identical on each machine after fresh install
- `skills.local/` is NOT ignored — custom/local-only skills DO sync
- Everything config-related (config.yaml, SOUL.md, MEMORY.md, USER.md, IDENTITY.md, cron/, plugins/) is synced
- Everything runtime (sessions, logs, state.db, caches) is ignored

### 4. Write Config XML

Minimal config format (only required fields — syncthing fills defaults at runtime):

```xml
<configuration version="37">
    <folder id="hermes-config" label="Hermes Config"
            path="/home/<user>/.hermes" type="sendreceive"
            rescanIntervalS="60" fsWatcherEnabled="true"
            fsWatcherDelayS="10" ignorePerms="false"
            autoNormalize="true">
        <device id="LOCAL_DEVICE_ID"/>
        <device id="PEER_1_DEVICE_ID"/>
        <device id="PEER_2_DEVICE_ID"/>
        <device id="PEER_3_DEVICE_ID"/>
        <minDiskFree unit="%">1</minDiskFree>
        <paused>false</paused>
    </folder>
    <device id="LOCAL_DEVICE_ID" name="hostname">
        <address>dynamic</address>
    </device>
    <device id="PEER_1_DEVICE_ID" name="peer-name">
        <address>dynamic</address>
    </device>
    ...
    <gui enabled="true" tls="false">
        <address>127.0.0.1:8384</address>
        <apikey>some-unique-api-key</apikey>
    </gui>
    <options>
        <listenAddress>default</listenAddress>
        <globalAnnounceEnabled>true</globalAnnounceEnabled>
        <localAnnounceEnabled>true</localAnnounceEnabled>
        <announceLANAddresses>true</announceLANAddresses>
        <setLowPriority>true</setLowPriority>
    </options>
</configuration>
```

**Critical:** Config is at `~/.local/state/syncthing/config.xml` on modern syncthing installs, NOT `~/.config/syncthing/config.xml`. Verify with `find ~ -name 'config.xml' -path '*syncthing*' | grep -v android`.

### 5. Start Syncthing

**Via systemd user service** (lin, macuntu — user accounts):

```bash
systemctl --user enable --now syncthing
```

**Via systemd system service** (kubuntux — root):

```bash
cat > /etc/systemd/system/syncthing-root.service << 'EOF'
[Unit]
Description=Syncthing (root)
After=network.target

[Service]
Type=simple
Environment=HOME=/root
ExecStart=/usr/bin/syncthing serve --no-browser --no-restart
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now syncthing-root
```

**Without systemd** (non-systemd systems):

```bash
nohup syncthing serve --no-browser --no-restart &>/dev/null &
```

**Pitfall:** `$HOME is not defined` when running as root via systemd. Always set `Environment=HOME=/root` in the service definition.

### 6. Verify Connections

```bash
# Check connected devices
curl -s -X GET \
  -H "X-API-Key: $(grep apikey ~/.local/state/syncthing/config.xml | sed 's/.*<apikey>//;s/<\/apikey>.*//')" \
  http://127.0.0.1:8384/rest/system/connections | python3 -c "
import sys, json
d = json.load(sys.stdin)
for dev_id, info in d.get('connections', {}).items():
    print(f'{dev_id[:20]}... in: {info.get(\"inBytesTotal\",0)/1024/1024:.0f}MB  out: {info.get(\"outBytesTotal\",0)/1024/1024:.0f}MB')
"
```

### 7. Check Sync Status

```bash
curl -s -X GET \
  -H "X-API-Key: $(grep apikey ~/.local/state/syncthing/config.xml | sed 's/.*<apikey>//;s/<\/apikey>.*//')" \
  http://127.0.0.1:8384/rest/db/status?folder=hermes-config | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'State: {d.get(\"state\")}')
print(f'Global: {d.get(\"globalFiles\",0)} files / {d.get(\"globalBytes\",0)/1024/1024:.0f}MB')
print(f'Need: {d.get(\"needFiles\",0)} files / {d.get(\"needBytes\",0)/1024/1024:.0f}MB')
"
```

## Pitfalls

- **Config file corruption from string replace.** Using `sed`, `patch`, or Python string `replace()` to add device IDs to an existing XML config is error-prone — the device ID is a long base32 string and partial matches cause concatenation (`ID1-ID2`). Always write the full config fresh from scratch.
- **XML format matters.** Device elements inside a folder use `<device id="..."/>` (self-closing). Device elements in the top-level device list use `<device id="..." name="..."><address>dynamic</address></device>` (with address child). Wrong format = parse failure.
- **service restart failure after config write.** After writing a config, `systemctl --user start syncthing` may fail with `Start request repeated too quickly`. Run `systemctl --user reset-failed syncthing` first, then start.
- **Initial scan picks up files before stignore loads.** When you first add the folder, syncthing indexes everything including files that should be ignored. The stignore takes effect on the next rescan. To force re-evaluation: `curl -X POST "http://127.0.0.1:8384/rest/db/scan?folder=hermes-config"`.
- **NFS symlinks get replaced by syncthing.** If a machine previously had `skills -> /mnt/nfs/skills` and you add the same path as a syncthing folder, syncthing follows the symlink and replaces it with a real directory containing the NFS contents. This actually breaks the NFS dependency automatically — the data ends up local.
- **Port 22000 and 21027** must be reachable between machines. Tailscale mesh handles this automatically since it's all local to the mesh. For machines not on the same Tailscale network, configure port forwarding or use relay servers.
- **API key extraction from config.** `grep apikey config.xml | sed 's/.*<apikey>//;s/<\/apikey>.*//'` works reliably. Don't hardcode API keys in scripts — extract them at runtime.

## Comparison: Syncthing vs NFS vs Git

| Feature | Syncthing (P2P) | NFS | Git |
|---------|-----------------|-----|-----|
| Auto-sync | ✓ Real-time | ✓ Instant (mounted) | ✗ Manual push/pull |
| No boot dependency | ✓ Daemon starts with system | ✗ fstab blocks boot if NAS down | ✓ |
| No single point of failure | ✓ Full mesh | ✗ NAS must be online | ✓ (GitHub) |
| Conflict resolution | ✓ Built-in (file versioning) | ✗ Last-write-wins | ✓ Merge |
| Bandwidth efficiency | ✓ Deltas only | ✓ No transfer (shared) | ✗ Full objects |
| Setup complexity | Medium | High (server + client) | Low |
| Works offline | ✓ Local copy cached | ✗ Requires mount | ✓ Local repo |

**Recommendation:** Syncthing for any multi-machine setup with a Tailscale mesh. Only use NFS for read-only shared data that's too large to replicate (e.g., a shared model cache). Git only for things that need history/diff.
