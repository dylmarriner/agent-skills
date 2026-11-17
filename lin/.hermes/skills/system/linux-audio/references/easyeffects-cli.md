---
name: easyeffects-cli
description: Configure EasyEffects DSP chains programmatically via dconf — EQ bands, multiband compressor, limiter, autogain, plugin ordering, and output routing. No GUI needed.
allowed-tools: Terminal Grep
metadata:
  tags: audio, equalizer, dsp, easyeffects, dconf, pipewire
---

# EasyEffects CLI (dconf)

Configure EasyEffects' DSP chain entirely through dconf — useful for automation, headless setup, or when the GUI is unavailable.

## When to use

- Setting up system-wide audio EQ without opening the GUI
- Automating audio DSP configuration in setup scripts
- Debugging or diagnosing EasyEffects routing
- Restoring a known-good DSP chain after a reset

## Architecture

EasyEffects stores all plugin configuration in dconf under:
- `/com/github/wwmm/easyeffects/` — global settings
- `streamoutputs/` — output (speaker) processing chain
- `streaminputs/` — input (microphone) processing chain
- `streamoutputs/<plugin>/0/` — per-plugin-instance settings

The plugin chain order is controlled by a single key:
```
/com/github/wwmm/easyeffects/streamoutputs/plugins
```
This is a string array like `['equalizer#0', 'multibandcompressor#0', 'limiter#0', 'autogain#0']`.

## Common Operations

### Set the processing chain
```bash
dconf write /com/github/wwmm/easyeffects/streamoutputs/plugins \
  "['equalizer#0', 'multibandcompressor#0', 'limiter#0', 'autogain#0']"
```

### Set the output device
```bash
dconf write /com/github/wwmm/easyeffects/streamoutputs/output-device \
  "'alsa_output.pci-0000_01_00.1.hdmi-stereo-extra5'"
dconf write /com/github/wwmm/easyeffects/streamoutputs/use-default-output-device false
```

### Reset to defaults
```bash
dconf reset -f /com/github/wwmm/easyeffects/
```

### Check the active chain
```bash
dconf read /com/github/wwmm/easyeffects/streamoutputs/plugins
```

## Available Plugins and Their dconf Keys

### Equalizer (equalizer#0)
Location: `com.github.wwmm.easyeffects.streamoutputs.equalizer.0`
Schema: `/usr/share/glib-2.0/schemas/com.github.wwmm.easyeffects.*.gschema.xml`

Key settings:
- `num-bands` — number of active bands (max 30, but ~10 is standard)
- `output-gain` — master output gain in dB
- Left channel bands at `leftchannel/band{N}-{type,frequency,gain,q}`

Each band has:
- `type`: `"'Off'"`, `"'Bell'"`, `"'Lo-shelf'"`, `"'Hi-shelf'"`, `"'High-pass'"`, `"'Low-pass'"`, `"'Notch'"`, `"'Band-pass'"`
- `frequency`: center frequency in Hz
- `gain`: boost/cut in dB
- `q`: filter Q/width

### Multiband Compressor (multibandcompressor#0)
Schema keys:
- `compressor-mode`: `"'Classic'"`, `"'Modern'"`, `"'Linear Phase'"`
- `enable-band{N}`: true/false (N=1..7)
- `split-frequency{N}`: crossover frequencies
- `attack-threshold{N}`: threshold in dB (range -60..0)
- `attack-time{N}`: ms (range 0..2000)
- `release-time{N}`: ms (range 0..5000)
- `ratio{N}`: compression ratio (range 1..100)
- `knee{N}`: knee in dB (range -24..0)

### Limiter (limiter#0)
Key settings:
- `mode`: `"'Herm Thin'"`, `"'Herm Wide'"`, `"'Herm Tail'"`, `"'Herm Duck'"`, etc.
- `threshold`: limit threshold in dB
- `attack`: attack in ms
- `release`: release in ms
- `lookahead`: lookahead in ms (range 0.1..20)

### AutoGain (autogain#0)
- `target`: loudness target in LUFS (default -20.0)
- `reference`: `"'Geometric Mean (MSI)'"` or similar

## Applying Changes

EasyEffects reads dconf on startup. If EE is already running:
1. Write the dconf values
2. Restart EE:
   ```bash
   gdbus call --session --dest com.github.wwmm.easyeffects \
     --object-path /com/github/wwmm/easyeffects \
     --method org.gtk.Actions.Activate "quit" "[[]]" "{}"
   ```
3. It will restart on next D-Bus call

To trigger re-activation:
```bash
gdbus call --session --dest com.github.wwmm.easyeffects \
  --object-path /com/github/wwmm/easyeffects \
  --method org.freedesktop.DBus.Peer.Ping
```

## Pitfalls

- **GTK4 settings can crash EasyEffects**: Remove `gtk-modules` from `~/.config/gtk-4.0/settings.ini` if EasyEffects segfaults.
- **Reset before reconfiguring**: If EE crashes on startup, do `dconf reset -f /com/github/wwmm/easyeffects/` first, then verify EE starts, then apply your config.
- **Plugin order matters**: Process chain runs in array order. Standard studio chain: EQ → Multiband Compressor → Limiter → AutoGain.
- **Multiband compressor bands are 1-indexed** in `enable-band{N}` but **0-indexed** in per-band params like `attack-threshold{N}`.
- **dconf path syntax**: Use forward slashes for paths in `dconf write`, not dots.
- **String values**: Must be quoted twice: `"'Bell'"` (outer shell quotes + inner dconf quotes).
