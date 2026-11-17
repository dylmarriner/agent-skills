---
name: linux-audio-routing-dsp
description: Configure PipeWire/Pulse audio routing and apply real-time DSP (EQ, limiter, gate) via Easy Effects or manual filter chains on Linux. Covers HDMI/optical/USB sink setup, autoload configuration, and DSP presets for common gear (Sonos, AV receivers, headphones).
---

# Linux Audio Routing & DSP

Apply software DSP to a specific audio sink on Linux (PipeWire era) — usually to compensate for downstream gear that has poor or fixed EQ (soundbars, TVs, budget DACs).

## When to load this skill

- User wants to EQ audio for a specific output device (soundbar, speakers, headphones) on Linux
- Easy Effects autoload, presets, or filter chain not engaging
- Sink auto-detection of new monitors / reconnection
- Building a per-device EQ curve
- TV/optical/HDMI signal chain needs source-side compensation

## Signal chain model

Always trace the full path before applying DSP. Common Linux setups:

- **PC → HDMI → TV → optical/SPDIF → Soundbar (+ Sub)**: the TV is in the loop. Source-side EQ is the only controllable point. The TV may add its own processing (look for "Surround", "Dynamic Range", "Game Mode", "PC Mode"). For accurate audio, set TV to PCM stereo, disable all TV sound modes, and disable downstream device's own EQ (e.g. Sonos Loudness, Night Mode, Speech Enhancement).
- **PC → USB DAC → speakers/headphones**: clean path, DSP at source is the only EQ available.
- **PC → BT → headphones**: avoid EQ — codec adds latency and re-encoding distorts the curve. DSP goes before the BT stream if at all.

## Easy Effects (EE) v7.1.6 specifics

This is the Ubuntu 24.04 package version. Known issue: **segfaults in `libsigc-3.0.so.0.0.0`** when system libsigc++ is 3.6.x. Symptoms:

- `easyeffects --load-preset X` segfaults instantly
- `--gapplication-service` mode starts then dies, D-Bus name briefly appears then vanishes
- `dmesg` shows `easyeffects[...]: segfault ... in libsigc-3.0.so.0.0.0`
- Multiple PIDs in the strace output all hit SIGSEGV

**Workaround**: install the Flathub build (`com.github.wwmm.easyeffects` from `flathub`). Use `flatpak run com.github.wwmm.easyeffects//master` (the `master` branch ref is what Flathub serves — `//stable` may register as a different ref on some installs).

If you must use the native package, pin `libsigc++-3.0-0` to the 3.4.x version EE was built against, or build from source against the system libsigc.

## EE autoload file format (v7.1.6, source-verified)

The autoload entry is **NOT** named after the device description. From `presets_manager.cpp` `add_autoload()`:

```
output_file = autoload_output_dir / (device_name + ":" + device_profile + ".json")
```

Where:
- `device_name` = PipeWire node name, e.g. `alsa_output.pci-0000_01_00.1.hdmi-stereo-extra5`
- `device_profile` = ALSA profile name, e.g. `hdmi-stereo-extra5`

JSON content:
```json
{
  "device": "alsa_output.pci-0000_01_00.1.hdmi-stereo-extra5",
  "device-description": "Ellesmere HDMI Audio [Radeon RX 470/480 / 570/580/590] Digital Stereo (HDMI 6)",
  "device-profile": "hdmi-stereo-extra5",
  "preset-name": "My Preset Name"
}
```

Get the values from `pw-dump | jq` or `pactl list sinks`.

**Pitfall**: `device-description` often contains `/` (e.g. "RX 470/480"), `[]`, `()`, spaces — making it a valid autoload *payload* but a **broken filename** if you try to use it as one. Always use `device_name:device_profile.json`.

## Preset directory layout

```
~/.config/easyeffects/
├── output/                  # Live state of filter chain (per-device, auto-managed)
│   ├── presets/             # User-saved presets (selectable in UI)
│   │   └── My Preset.json
│   └── My Preset.json       # When saved, also appears as live config
├── input/                   # Same structure for input/mic chain
└── autoload/
    ├── output/
    │   └── <device_name>:<device_profile>.json
    └── input/
        └── <device_name>:<device_profile>.json
```

`gsettings` keys to know:
- `com.github.wwmm.easyeffects.process-all-outputs` — bool. If true, EE auto-attaches a filter to every output sink (no autoload file needed, but uses last-used preset).
- `com.github.wwmm.easyeffects.last-used-output-preset` — string.

## EQ band configuration gotchas

- **Mirror L/R**: EE's `equalizer#0` block has `left` and `right` sub-blocks. They must be identical for a stereo image.
- **Bands 0 and N-1**: use shelf types (Lo-shelf, Hi-shelf). Middle bands use Bell.
- **Q vs width**: EE uses both depending on filter mode. For `RLC (BT)`, set `mode: "RLC (BT)"` and `width: 4.0` (default). The `q` field is still respected.
- **Slope**: `x1`, `x2`, `x4` etc. for shelf steepness. Stick to `x1` for soundbar/room correction.
- **num-bands vs actual bands**: must be set explicitly (e.g. 10), and the `band0`..`band9` keys must exist.
- **split-channels: false** is what you want for stereo mirroring.

## Reference curve: Sonos Playbar + Sub (TV/optical)

Starting point for 10-band IIR, L=R, when TV and Sonos app processing are disabled:

| band | type | freq | gain | Q |
|---|---|---|---|---|
| 0 | Lo-shelf | 25 Hz | -4.0 dB | 0.70 |
| 1 | Bell | 50 Hz | -1.5 dB | 0.80 |
| 2 | Bell | 80 Hz | -1.0 dB | 0.90 |
| 3 | Bell | 160 Hz | +0.5 dB | 1.10 |
| 4 | Bell | 250 Hz | -2.5 dB | 1.20 |
| 5 | Bell | 500 Hz | -1.0 dB | 1.00 |
| 6 | Bell | 1.5 kHz | +1.5 dB | 0.90 |
| 7 | Bell | 3 kHz | +2.0 dB | 0.80 |
| 8 | Bell | 8 kHz | -1.0 dB | 1.10 |
| 9 | Hi-shelf | 16 kHz | +0.5 dB | 0.70 |

Rationale: subsonic cut at 25 Hz (sub port noise), Sub crossover at ~80 Hz, -2.5 dB at 250 Hz to clear Playbar boxiness, +1.5/+2 dB at 1.5/3 kHz for dialogue lift (soundbars need it), gentle 8 kHz cut, air shelf at 16 kHz.

## Verifying the filter is actually engaged

EE creates a PipeWire node per engaged sink. Check:

```bash
pw-dump | jq '.[] | select(.info.props["media.class"] | test("Filter"))'
```

You should see an `Audio/Filter/Stream` (or similar) node that is linked between apps and the physical sink. If you only see raw ALSA sinks and no Filter node, the EE engine is not engaged.

## Common pitfalls

1. **EE service started but no filter node** — usually the autoload JSON file is named wrong (description instead of `name:profile`), or the engine crashed. Check `dmesg` for segfaults, `journalctl --user -u app-easyeffects*` for the service log.
2. **Audio plays but EQ has no effect** — the PipeWire filter node exists but isn't in the audio graph. Check `wpctl status` for links. Sometimes killing the EE app and restarting the audio source re-links it.
3. **TV adds its own EQ** — disable TV "Surround", "Dynamic Range Compression", "Bass Boost", "Game Mode" audio. Set to "PCM Stereo" or "PC Mode" if available.
4. **Downstream device has its own EQ** — disable on Sonos app: Loudness, Night Mode, Speech Enhancement, EQ sliders all to 0/Off. Otherwise you stack two curves.
5. **Optical output is stereo-only PCM** — Sonos over optical takes PCM stereo, not DD/DTS. The TV must be set to output stereo PCM, not passthrough. Set TV sound output to "PCM" or "Stereo".
6. **Chromecast / casting** changes the signal chain — bypass EE entirely. Don't try to EQ cast streams.
7. **Flatpak vs native EE config isolation** — Easy Effects installed via Flatpak reads/writes a separate config dir (`~/.var/app/com.github.wwmm.easyeffects/config/easyeffects/`), not `~/.config/easyeffects/`. Presets, autoload files, and live state written to the native path are invisible to the flatpak build, and vice versa. If you switch packaging, copy the config across: `cp -r ~/.config/easyeffects/* ~/.var/app/com.github.wwmm.easyeffects/config/easyeffects/`. Check which one EE is actually using with `ps -ef | grep easyeffects | grep -v grep` — `bwrap` in the path means flatpak.
8. **Preset exists on disk but isn't loaded** — having the JSON file in `~/.config/easyeffects/output/presets/` does not mean EE has applied it. Verify with `pw-dump | grep Filter` for a filter node linked to the target sink. If only the raw ALSA sinks are visible, the autoload entry is missing, the file is in the wrong config dir, or EE hasn't refreshed. Restart EE to force re-read.
9. **"I did X" without verifying the audio chain** — do not claim an EQ is applied until you've confirmed a PipeWire filter node is linked to the target sink. The user will catch this if you skip it.

## Manual PipeWire filter-chain fallback

If EE is unusable, you can apply a `filter-chain` directly via `pw-cli`:

```bash
# load-module filter-chain is part of pipewire
# See /usr/share/pipewire/filter-chain/*.json for examples
pw-cli load-module libpipewire-module-filter-chain \
  node.name=eq node.description="Manual EQ" \
  filter.graph="..."  # biquad cascade
```

This is more brittle (no preset management, no live editing) but bypasses the EE GUI. Only use if EE is unrecoverable.

## Reference: getting device identifiers

```bash
# PipeWire node name + description
pw-cli ls Node | grep -A2 "alsa_output"

# wpctl (wireplumber)
wpctl status
wpctl inspect @DEFAULT_SINK@

# ALSA / PulseAudio compat
pactl list sinks short
```

## Related support files

- `references/easyeffects-libsigc-segfault.md` — full diagnostic transcript and Flathub install procedure
- `references/autoload-filename-formats.md` — format across EE versions
- `templates/playbar-sub-eq.json` — ready-to-use preset JSON for the Sonos Playbar + Sub EQ curve
- `templates/autoload-skeleton.json` — autoload file template with placeholders
- `scripts/dump-ee-state.sh` — inspect running EE state, autoload entries, and PipeWire filter nodes
