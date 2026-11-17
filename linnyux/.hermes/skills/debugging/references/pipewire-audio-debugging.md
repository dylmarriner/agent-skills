# PipeWire / WirePlumber Audio Debugging

## Common Failure: WirePlumber Dead → "No Audio Devices"

**Symptom**: `pactl list sinks` shows only virtual/null sinks, no hardware devices.
`wpctl status` shows no devices under Audio → Devices.
`aplay -l` does show ALSA hardware (so drivers are fine).

**Root cause**: WirePlumber (PipeWire's session manager) has crashed or exited. Without it, PipeWire can't discover ALSA hardware.

**Diagnosis**:
```bash
# Check if WirePlumber is running
systemctl --user status wireplumber

# Expected: "active (running)"
# Actual:   "inactive (dead)"
```

**Fix**:
```bash
systemctl --user start wireplumber
```

After starting WirePlumber, hardware devices appear within 1-2 seconds.

## Common Failure: EasyEffects Segfaults

**Symptom**: `easyeffects --version` or any invocation segfaults (exit code 139).
GTK warnings about unknown keys.

**Root cause**: GTK 4.0 settings corruption, typically:
- `gtk-modules` line in `~/.config/gtk-4.0/settings.ini` referencing missing modules
- Dark theme conflict with Adwaita/libadwaita

**Fix**:
1. Remove `gtk-modules` line from `~/.config/gtk-4.0/settings.ini`
2. Reset EasyEffects dconf: `dconf reset -f /com/github/wwmm/easyeffects/`
3. Reactivate via D-Bus: `gdbus call --session --dest com.github.wwmm.easyeffects ... Ping`

**If still crashing**, EasyEffects is likely broken on this GTK4/Mesa combination — use PipeWire filter-chain or pw-loopback as an alternative.

## Audio Routing: Creating a Processing Chain Without EasyEffects

When EasyEffects is broken, create the chain directly:
```bash
# 1. Create null sink
pw-cli create-node adapter '{ factory.name=support.null-audio-sink node.name=easyeffects_sink media.class=Audio/Sink }'

# 2. Set as default
pactl set-default-sink easyeffects_sink

# 3. Route null sink output to HDMI
pw-link easyeffects_sink:monitor_FL alsa_output.pci-0000_01_00.1.hdmi-stereo-extra5:playback_FL
pw-link easyeffects_sink:monitor_FR alsa_output.pci-0000_01_00.1.hdmi-stereo-extra5:playback_FR
```

## Configuring EasyEffects Programmatically (via dconf)

When EasyEffects IS running, configure its DSP chain entirely via dconf:

```bash
# Set plugin chain order
dconf write /com/github/wwmm/easyeffects/streamoutputs/plugins \
  "['equalizer#0', 'multibandcompressor#0', 'limiter#0', 'autogain#0']"

# Set output device
dconf write /com/github/wwmm/easyeffects/streamoutputs/output-device \
  "'alsa_output.pci-0000_01_00.1.hdmi-stereo-extra5'"

# Configure EQ bands (10-band parametric)
BASE="/com/github/wwmm/easyeffects/streamoutputs/equalizer/0"
dconf write $BASE/num-bands 10
dconf write $BASE/output-gain -0.5

# Set per-band parameters
band_type="'Bell'"
dconf write ${BASE}/leftchannel/band0-type "'Lo-shelf'"
dconf write ${BASE}/leftchannel/band0-frequency 31.0
dconf write ${BASE}/leftchannel/band0-gain 2.0
dconf write ${BASE}/leftchannel/band0-q 0.7

# Multiband compressor (4 bands)
MBC="/com/github/wwmm/easyeffects/streamoutputs/multibandcompressor/0"
dconf write $MBC/compressor-mode "'Modern'"
dconf write $MBC/enable-band1 true; dconf write $MBC/enable-band2 true
dconf write $MBC/enable-band3 true; dconf write $MBC/enable-band4 true
dconf write $MBC/split-frequency1 200.0
dconf write $MBC/attack-threshold0 -18.0
dconf write $MBC/ratio0 2.0

# Limiter
LIM="/com/github/wwmm/easyeffects/streamoutputs/limiter/0"
dconf write $LIM/threshold -3.0
dconf write $LIM/attack 2.0
dconf write $LIM/release 10.0

# Autogain (loudness normalization)
AG="/com/github/wwmm/easyeffects/streamoutputs/autogain/0"
dconf write $AG/target -20.0
```

**Note**: EasyEffects must be restarted after dconf changes to pick them up:
```bash
gdbus call --session --dest com.github.wwmm.easyeffects ... quit
# Then D-Bus activation on next connection
```
