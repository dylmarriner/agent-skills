---
name: linux-audio
description: Diagnose and fix PipeWire audio issues, configure audio routing, set up EasyEffects or PipeWire filter-chain EQ, and build adaptive EQ pipelines on Linux.
---

# Linux Audio Troubleshooting & EQ Setup

## Triggers
Use this skill when:
- User reports "no sound" or "audio device not found"
- EasyEffects / PipeWire audio chain is broken
- User wants to set up system-wide EQ
- Building audio processing pipelines with PipeWire
- Creating or debugging null sinks, filter chains, or loopback devices

## Step 1: Diagnose the Audio Stack

### Check service health
```bash
systemctl --user status pipewire
systemctl --user status pipewire-pulse
systemctl --user status wireplumber
```

**Key diagnostic: WirePlumber** is the session manager that discovers ALSA hardware. If it's **inactive (dead)**, PipeWire runs but sees zero devices. Restart it:
```bash
systemctl --user start wireplumber
```
The libcamera warning (`SPA handle 'api.libcamera.enum.manager'`) is harmless.

### List available hardware
```bash
aplay -l                          # ALSA hardware
wpctl status                      # PipeWire node tree
pw-cli list-objects Node | grep -E "node.name|node.description"
pw-link -l                        # Full link graph
pactl list cards                  # Card profiles (analog, HDMI, S/PDIF)
pactl list sinks                  # Active outputs with volume/mute
```

## Step 2: Audio Routing Fixes

| Problem | Check | Fix |
|---------|-------|-----|
| WirePlumber dead | `systemctl --user status wireplumber` | `systemctl --user start wireplumber` |
| Wrong card profile | `pactl list cards` → look for `Active Profile:` | `pactl set-card-profile <card> <profile>` |
| Sink at 0% volume | `pactl list sinks` → check dB value | `pactl set-sink-volume <sink> 100%` |
| Wrong default sink | `pactl get-default-sink` | `pactl set-default-sink <sink>` |
| Analog output "not available" | Jack detection false-negative | Switch profile anyway — PipeWire often accepts it |
| Analog output sink missing | No `analog-stereo` profile active | `pactl set-card-profile alsa_card.pci-0000_00_1f.3 output:analog-stereo+input:analog-stereo` |

### Example: HDMI to TV to Optical to Soundbar
```bash
pactl set-default-sink alsa_output.pci-0000_01_00.1.hdmi-stereo-extra5
# Audio path: PC -> HDMI -> TV -> Optical (S/PDIF) -> Soundbar
```

## Step 3: EasyEffects Setup

### When EasyEffects works (stays stable)
```bash
# List and load presets
easyeffects -p
easyeffects -l <preset_name>

# Check bypass status (0=active)
easyeffects -b 3

# Config files in ~/.config/easyeffects/output/
```

### Plugin chain order
Recommended: **Equalizer → Multiband Compressor → Limiter → AutoGain**

Configure via dconf (EasyEffects stores plugin parameters there, not in JSON):
```bash
dconf write /com/github/wwmm/easyeffects/streamoutputs/plugins \
  "['equalizer#0', 'multibandcompressor#0', 'limiter#0', 'autogain#0']"
```

### Multiband Compressor settings (4-band content-adaptive)
| Band | Freq Split | Threshold | Ratio | Attack | Release | Purpose |
|------|-----------|-----------|-------|--------|---------|---------|
| 1    | 20-200Hz  | -18dB     | 2:1   | 10ms   | 150ms   | Tight bass control |
| 2    | 200-800Hz | -15dB     | 1.5:1 | 15ms   | 120ms   | Smooth low-mid mud |
| 3    | 800-3kHz  | -12dB     | 1.5:1 | 10ms   | 80ms    | Vocal presence |
| 4    | 3kHz+     | -18dB     | 2:1   | 5ms    | 60ms    | Tame harshness |

Set via dconf:
```bash
MBC="/com/github/wwmm/easyeffects/streamoutputs/multibandcompressor/0"
dconf write $MBC/compressor-mode "'Modern'"
dconf write $MBC/enable-band1 true
dconf write $MBC/enable-band2 true
dconf write $MBC/enable-band3 true
dconf write $MBC/enable-band4 true
dconf write $MBC/split-frequency1 200.0
dconf write $MBC/split-frequency2 800.0
dconf write $MBC/split-frequency3 3000.0
dconf write $MBC/attack-threshold0 -18.0
dconf write $MBC/attack-threshold1 -15.0
dconf write $MBC/attack-threshold2 -12.0
dconf write $MBC/attack-threshold3 -18.0
dconf write $MBC/ratio0 2.0
dconf write $MBC/ratio1 1.5
dconf write $MBC/ratio2 1.5
dconf write $MBC/ratio3 2.0
```

### Limiter settings
```bash
LIM="/com/github/wwmm/easyeffects/streamoutputs/limiter/0"
dconf write $LIM/threshold -3.0
dconf write $LIM/attack 2.0
dconf write $LIM/release 10.0
dconf write $LIM/lookahead 5.0
```

### Apply EQ bands via dconf
```bash
BASE="/com/github/wwmm/easyeffects/streamoutputs/equalizer/0"
LC="$BASE/leftchannel"
dconf write $BASE/num-bands 10
dconf write $BASE/output-gain -0.5
# Band 0: 31Hz Lo-shelf +2.0dB Q0.7
dconf write $LC/band0-type "'Lo-shelf'"
dconf write $LC/band0-frequency 31.0
dconf write $LC/band0-gain 2.0
dconf write $LC/band0-q 0.7
# Band 1: 63Hz Bell +1.5dB Q0.8
dconf write $LC/band1-type "'Bell'"
dconf write $LC/band1-frequency 63.0
dconf write $LC/band1-gain 1.5
dconf write $LC/band1-q 0.8
# Repeat for bands 2-9 (Bell type except band9=Hi-shelf)
```

## Step 4: PipeWire Filter-Chain EQ (EasyEffects Crash Workaround)

**When EasyEffects segfaults** (GTK4/Adwaita/Mesa crash — common with broken `~/.config/gtk-4.0/settings.ini` or GPU driver issues), use PipeWire's built-in filter-chain instead.

### Fix the GTK config that causes EasyEffects crashes
```bash
sed -i '/gtk-modules=/d' ~/.config/gtk-4.0/settings.ini
```

### PipeWire filter-chain with biquad filters
Create `~/.config/pipewire/filter-chain.conf.d/10-eq.conf`. See the `references/pipewire-filter-chain.md` file for a full 10-band template.

**Available biquad filter labels:** `bq_lowshelf`, `bq_highshelf`, `bq_peaking`, `bq_lowpass`, `bq_highpass`, `bq_bandpass`, `bq_notch`, `bq_allpass`.

**Controls per filter:** `"Freq"` (Hz), `"Q"` (bandwidth), `"Gain"` (dB).

### Load filter chain
```bash
systemctl --user restart pipewire pipewire-pulse wireplumber
```

### Control filter params at runtime (useful for adaptive EQ)
```bash
pw-cli set-param <node_name> port '{ "eq_band_0:Gain" = 1.5 }'
```

## Step 5: Null Sink and Routing (No EasyEffects)

When EasyEffects is broken, create a virtual null sink and route manually:

### Create null sink
```bash
pw-cli create-node adapter "{ factory.name=support.null-audio-sink node.name=my_sink media.class=Audio/Sink audio.position=FL,FR }"
```

### Route audio through a filter chain
```bash
# Set as default so apps route to it
pactl set-default-sink my_sink
# Connect null sink monitor to filter chain input
pw-link my_sink:monitor_FL eq_input:input_FL
pw-link my_sink:monitor_FR eq_input:input_FR
# Connect EQ output to HDMI
pw-link eq_output:output_FL hdmi_sink:playback_FL
pw-link eq_output:output_FR hdmi_sink:playback_FR
```

## Step 6: AI-powered Adaptive EQ (Architecture)

For a system that analyzes audio and adjusts EQ in real-time:

### Design
1. **Capture** system audio via PipeWire stream capture on the null sink monitor
2. **Analyze** with FFT (2048 bins, Hann window, 120Hz update rate)
3. **Profile** with rolling EMAs: short-term (~0.5s) and long-term (~3s)
4. **Compare** each band's relative energy against a target curve (reference = 1kHz)
5. **Correct** with smoothed attack (~2s) and release (~5s) envelopes
6. **Apply** via `pw-cli set-param` on the filter-chain node

### Target curve (relative to 1kHz)
| Freq | Target (dB re:1kHz) |
|------|-------------------|
| 31   | +2.0              |
| 63   | +1.0              |
| 125  | -2.0              |
| 250  | -3.0              |
| 500  | -1.0              |
| 1k   | 0.0 (reference)   |
| 2k   | +1.0              |
| 4k   | +0.5              |
| 8k   | -1.0              |
| 16k  | -2.0              |

### Key constraints
- **No duplicate FFT** — if the DSP crate already computes FFT, accept band energies instead of raw samples
- **Silence gate** with exponential smoothing — don't EQ during quiet passages (prevents hunting)
- **Cross-band smoothing** — adjacent bands (0.3 weight) prevent jagged curves
- **Clamp adjustments** to +/-3dB per band to avoid over-correction
- **Normalize** band energies by total energy before comparing to target

## Verify with a test tone
```bash
speaker-test -c 2 -l 1 -t pink -r 48000
```

## Pitfalls

- **WirePlumber can crash silently** — PipeWire and PipeWire-Pulse keep running. Always check `systemctl --user status wireplumber`.
- **EasyEffects segfaults** — GTK4 crashes with bad `~/.config/gtk-4.0/settings.ini` (remove `gtk-modules=` line) or Mesa `vblank_mode` issues. If `easyeffects --version` itself segfaults, don't fight it — use PipeWire filter-chain instead.
- **EasyEffects resets on crash** — all dconf plugin config is lost. Reset with `dconf reset -f /com/github/wwmm/easyeffects/` then reconfigure.
- **`easyeffects_sink` disappears** after EasyEffects crashes — it is a virtual node created by EE, not persistent. Recreate with `pw-cli create-node adapter` or restart EE.
- **Filter-chain conf.d not auto-loaded** — PipeWire 1.0.5 does not scan `~/.config/pipewire/filter-chain.conf.d/` automatically unless referenced from main `pipewire.conf`. Restart `pipewire.service` to re-read.
- **AutoGain compression** — can squash dynamics on mastered content. Bypass if audio sounds flat.
- **HDMI volume is at ALSA level** — not TV volume. Check with `pactl list sinks`.
- **`pw-link` connections are ephemeral** — lost on PipeWire restart. Use a startup script or systemd service to recreate.
