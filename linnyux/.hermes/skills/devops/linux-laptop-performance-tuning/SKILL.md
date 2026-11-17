---
name: linux-laptop-performance-tuning
description: Diagnose and improve Linux laptop responsiveness, battery/performance tradeoffs, thermals, startup latency, and background load.
---

# Linux Laptop Performance Tuning

Use this skill when the user wants a Linux laptop to feel faster, boot quicker, run cooler/quieter, improve battery life, or reduce idle/background overhead.

## Scope

Covers:
- CPU governor and scaling behavior
- thermals, fan curves, throttling, and power limits
- boot/startup analysis and service trimming
- background process audit
- memory pressure, swap, zram, and vm tuning
- disk I/O bottlenecks, filesystem-mount review, and hard drive / SSD cleanup and optimization
- desktop environment startup overhead
- GPU/power-profile selection where applicable
- safe, reversible tuning recommendations

Does not cover:
- hardware replacement advice beyond identifying likely bottlenecks
- risky kernel patching or unsupported overclocking by default
- distro-specific package management unless needed for a fix

## Instructions

1. Start by identifying the current environment: distro, kernel, desktop, power manager, and whether the machine is AC or battery constrained.
2. Measure before changing anything. Prefer live evidence from `systemd-analyze`, `top/htop`, `ps`, `free`, `vmstat`, `iotop`, `powertop`, `thermald`, `sensors`, `journalctl`, `cat /proc/cpuinfo`, `lscpu`, and relevant vendor tools.
3. Separate symptoms into categories:
   - boot/login slowness
   - interactive lag
   - thermal throttling
   - battery drain
   - background service overhead
   - storage latency
   - memory pressure
4. Recommend the least risky fix first. Prefer configuration changes over aggressive tuning.
5. Make changes incrementally and keep reversibility in mind. Record what was changed and how to undo it.
6. If you propose commands, make them copy-pasteable, explain the effect briefly, and include a verification command.
7. If uncertainty remains, state it clearly and suggest the next measurement instead of guessing.

## Default workflow

- Check boot time and blame:
  - `systemd-analyze time`
  - `systemd-analyze blame`
  - `systemd-analyze critical-chain`
- Check thermal and CPU behavior:
  - `lscpu`
  - `sensors`
  - `turbostat` if available
  - `powertop` if available
- Check memory and swap:
  - `free -h`
  - `swapon --show`
  - `sysctl vm.swappiness`
- Check background load:
  - `top -b -n 1`
  - `ps aux --sort=-%cpu | head`
  - `ps aux --sort=-%mem | head`
- Check services:
  - `systemctl --type=service --state=running`
  - disable only clearly unnecessary services after confirming impact

## Common safe recommendations

- Enable/adjust a power profile manager if the laptop has one
- Reduce always-on desktop services that are not needed
- Use zram on memory-constrained systems
- Tune swappiness only after confirming swap pressure
- Investigate thermal throttling before blaming CPU speed
- Prefer vendor-supported power tools over generic overclocking

## Output format

When responding, provide:
- likely bottleneck(s)
- evidence gathered
- recommended changes in priority order
- verification steps after each change
- rollback steps for any change that is not purely diagnostic

## Safety notes

- Avoid destructive commands.
- Never suggest blind disabling of core system services.
- Be explicit when a tuning change could trade performance for battery life or vice versa.

## Aggressive "don't care about battery" tuning

When the user explicitly says max-performance-no-compromise (battery life is a free variable), apply this full suite. Each subsection below can be applied independently.

### Tuned profile: accelerator-performance

```bash
sudo tuned-adm profile accelerator-performance
```

This disables higher-latency C-states (C8/C9/C10) which cause wakeup latency. More aggressive than `throughput-performance`. Other candidates: `latency-performance`.

### GRUB kernel parameters (requires reboot)

Edit `/etc/default/grub`:

```
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash mitigations=off processor.max_cstate=1 intel_idle.max_cstate=1 nowatchdog"
```

Then `sudo update-grub`.

| Parameter | Effect |
|---|---|
| `mitigations=off` | Disables CPU security mitigations (Spectre/Meltdown/etc) — ~5-10% CPU gain |
| `processor.max_cstate=1` | Prevents deep C-states that cause wakeup latency |
| `intel_idle.max_cstate=1` | Same, for the intel idle driver |
| `nowatchdog` | Frees a timer interrupt core |

### VM / sysctl tuning for NVMe SSDs

Create `/etc/sysctl.d/99-zzz-performance-tuning.conf` (prefix `99-zzz-` is deliberate — see Pitfalls below):

```
vm.dirty_ratio = 20
vm.dirty_background_ratio = 10
vm.dirty_expire_centisecs = 3000
vm.dirty_writeback_centisecs = 500
vm.vfs_cache_pressure = 200
vm.swappiness = 10
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 1024
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_fin_timeout = 15
fs.file-max = 2097152
kernel.sched_min_granularity_ns = 3000000
kernel.sched_wakeup_granularity_ns = 4000000
kernel.sched_migration_cost_ns = 500000
kernel.sched_nr_migrate = 32
vm.zone_reclaim_mode = 0
```

Apply: `sudo sysctl --system`

A complete tested copy of this file lives at `references/aggressive-sysctl.conf`.

### Service disable list (Ubuntu 24.04 safe-to-kill)

These are safe to disable for a dev laptop. Measured impact included in parentheses.

```bash
sudo systemctl disable --now plocate-updatedb.timer    # -30s boot time
sudo systemctl disable --now unattended-upgrades.service # no apt lock contention
sudo systemctl disable --now rsyslog.service             # journald handles logging
sudo systemctl disable --now kerneloops.service          # diagnostic only
sudo systemctl disable --now teamviewerd.service         # unless you use TeamViewer
sudo systemctl disable --now smartmontools.service       # not needed for NVMe daily
sudo systemctl disable --now apt-daily-upgrade.timer     # no random apt CPU spikes
sudo systemctl disable --now apt-daily.timer
```

Also consider `packagekit.service` and `iio-sensor-proxy.service` (screen rotation).

### Journald memory limit

```bash
sudo mkdir -p /etc/systemd/journald.conf.d/
sudo tee /etc/systemd/journald.conf.d/99-limit-journal.conf << 'EOF'
[Journal]
SystemMaxUse=200M
RuntimeMaxUse=50M
MaxFileSec=7day
EOF
sudo systemctl restart systemd-journald
```

### NVIDIA GPU performance mode

For laptops with NVIDIA dGPU (MX150/GTX/RTX series):

```bash
# Enable persistence mode
sudo nvidia-smi -pm 1

# Force P0 (max performance) state
nvidia-settings -a "[gpu:0]/GpuPowerMizerMode=1"

# Verify
nvidia-smi -q -d PERFORMANCE | grep "Performance State"
```

Should report `P0` instead of the default `P8` (powersave).

### KDE Plasma compositor tuning

```bash
kwriteconfig5 --file ~/.config/kwinrc --group Compositing --key Backend OpenGL
kwriteconfig5 --file ~/.config/kwinrc --group Compositing --key LatencyPolicy 1
kwriteconfig5 --file ~/.config/kwinrc --group Compositing --key MaxFps 120
kwriteconfig5 --file ~/.config/kwinrc --group Compositing --key RefreshRate 120
kwriteconfig5 --file ~/.config/kwinrc --group Compositing --key GlSmoothScale 1
kwriteconfig5 --file ~/.config/kwinrc --group Compositing --key AllowSoftwareCompositing false
kwriteconfig5 --file ~/.config/kwinrc --group Compositing --key GpuClampForce 0
```

Log out and back in (or `kwin_x11 --replace &`).

### Wi-Fi Power Management

Wi-Fi power management causes the wireless card to enter sleep states between packets, adding 5-10ms of latency and throttling throughput. Killing it is the single biggest latency improvement on Wi-Fi.

**Check current state:**
```bash
iwconfig wlo1 | grep "Power Management"
```

**Disable immediately:**
```bash
sudo iwconfig wlo1 power off
```

**Make permanent (systemd service):**
```bash
sudo tee /etc/systemd/system/wifi-perf.service << 'EOF'
[Unit]
Description=Wi-Fi performance tuning
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/iwconfig wlo1 power off
ExecStart=/sbin/ip link set dev wlo1 txqueuelen 10000
RemainAfterExit=true

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now wifi-perf.service
```

Effect: ping drops from ~15ms to ~7ms, throughput ~5% gain. Cost: slightly higher battery drain.

### DNS Switching

The default ISP or Quad9 DNS may be slower than alternatives. Switch to Cloudflare or Google for measurably lower lookup latency.

**Current DNS:**
```bash
resolvectl status | grep "DNS Servers"
```

**Switch to Cloudflare + Google:**
```bash
sudo resolvectl dns wlo1 1.1.1.1 1.0.0.1 8.8.8.8
```

**Make permanent** (edit `/etc/systemd/resolved.conf`):
```ini
[Resolve]
DNS=1.1.1.1 1.0.0.1 8.8.8.8
```

### Docker Resource Hog Identification

When the user reports slowness but has no visible apps open, check Docker containers — each running container consumes CPU + RAM even when idle.

**List all running containers with resource impact:**
```bash
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
```

**Check per-container RAM:**
```bash
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

**Top resource hogs (common):**
- Elasticsearch (`docker-es01-1`): ~2GB RAM. If not indexing, kill it.
- Frigate (video surveillance): ~500MB RAM + GPU for object detection.
- Honcho stack (AI memory): 4 containers, ~500MB total.
- Minio (S3 storage): only needed if actively storing files.

**Quick memory recovery:**
```bash
docker stop docker-es01-1 frigate
# Then drop page cache:
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
```

## Additional Hardware Tweaks

### Disable Internal Keyboard

For users who use an external keyboard and want to disable the built-in one. See `references/disable-internal-keyboard.md` for setup instructions using a systemd user service (`~/.config/systemd/user/disable-internal-kbd.service`).

## Pitfalls

- **sysctl.d file ordering.** `/etc/sysctl.d/` loads files alphabetically. If you have multiple `99-*.conf` files, later ones override earlier ones for the same key. Always use a name that sorts LAST (e.g. `99-zzz-performance-tuning.conf`) so your values aren't silently overridden by other configs. Verify with `sysctl <key>` after `sudo sysctl --system`.
- **plocate socket activation.** Disabling `plocate-updatedb.timer` is not enough if a socket-triggered unit exists — also `systemctl disable plocate-updatedb.service` and stop it immediately.
- **Snapd auto-refresh.** `snap refresh --list` runs daily by default and can spike CPU. Set `sudo snap set system refresh.timer="monthly"` to reduce frequency.
- **NVIDIA P-state persistence.** Without `nvidia-smi -pm 1`, the GPU drops back to P8 on idle even with PowerMizerMode=1. Always set persistence mode.
- **KDE kwinrc changes.** `kwriteconfig5` writes the file, but compositor won't reload until KWin restarts (log out/in or `kwin_x11 --replace &`).
- **Ananicy-CPP might be custom-installed.** If from source it lives at `/usr/local/bin/ananicy-cpp` with no system package. Check `dpkg -l ananicy-cpp` — if missing, check `/usr/local/bin/`.

## Memory Pressure Diagnosis

When the user says "I have nothing open" but RAM is 70%+ used:
1. Run `free -h` and look at `available`, not `used` (buff/cache inflates used).
2. Check `swap --show` — high swap usage means past/ongoing memory pressure.
3. Identify Docker container hogs: `docker stats --no-stream | grep -v "0.00%"`
4. The top 3 background RAM eaters are Elasticsearch (~2GB), Frigate (~500MB), and Honcho stacks (~500MB).
5. After stopping containers: `sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches`

See `references/memory-pressure-diagnosis.md` for the full workflow with exact commands.

## Field-tested notes from Ubuntu dev-laptop tuning sessions

- Always measure first; boot blame, memory pressure, and live process load were the most useful signals.
- Cleaning package caches, journald retention, thumbnail caches, and temp files produced a small but real storage win.
- The `accelerator-performance` tuned profile felt snappier than `throughput-performance` on AC power.
- Disabling clearly unnecessary background services gave a noticeable responsiveness boost, but socket units may need to be disabled too if a service immediately reactivates.
- Disk-copy / disk-clone jobs can dominate I/O and make the machine feel much slower even when CPU and RAM look fine.
- After each batch of changes, re-check `systemd-analyze blame` and the running service list to confirm the effect.
- On an HP Pavilion with i7-8550U + MX150, dropping plocate (-30s) + switching to accelerator-performance + mitigations=off gave the single biggest felt improvement.
