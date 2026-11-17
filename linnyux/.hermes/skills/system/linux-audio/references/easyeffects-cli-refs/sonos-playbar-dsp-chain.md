# Sonos Playbar + Sub — Studio Reference EQ & DSP Chain

Full configuration for a Sonos Playbar + Sub connected via PC → HDMI → TV → Optical.

## Audio Path

```
App → easyeffects_sink → Equalizer → Multiband Compressor → Limiter → AutoGain → HDMI → TV (optical out) → Sonos Playbar + Sub
```

## Script: Apply Full DSP Chain

```bash
#!/bin/bash
# Reset and apply complete DSP chain for Sonos Playbar + Sub

echo "Applying EIDOLON adaptive audio DSP chain..."

# 1. Reset EE to clean state (fixes crash-on-startup issues)
dconf reset -f /com/github/wwmm/easyeffects/ 2>/dev/null

# 2. Load plugins in order: EQ → MultibandCompressor → Limiter → AutoGain
dconf write /com/github/wwmm/easyeffects/streamoutputs/plugins \
  "['equalizer#0', 'multibandcompressor#0', 'limiter#0', 'autogain#0']"

# 3. Route to HDMI output
dconf write /com/github/wwmm/easyeffects/streamoutputs/output-device \
  "'alsa_output.pci-0000_01_00.1.hdmi-stereo-extra5'"
dconf write /com/github/wwmm/easyeffects/streamoutputs/use-default-output-device false

# 4. Configure 10-band EQ (Studio Reference Curve)
EQ="/com/github/wwmm/easyeffects/streamoutputs/equalizer/0"
LC="$EQ/leftchannel"
dconf write $EQ/num-bands 10
dconf write $EQ/output-gain -0.5
dconf write $EQ/split-channels false

# Band 0: 31Hz Lo-shelf +2dB Q0.7 — sub bass foundation
dconf write $LC/band0-type "'Lo-shelf'"
dconf write $LC/band0-frequency 31.0; dconf write $LC/band0-gain 2.0; dconf write $LC/band0-q 0.7

# Band 1: 63Hz Bell +1.5dB Q0.8 — bass fullness
dconf write $LC/band1-type "'Bell'"
dconf write $LC/band1-frequency 63.0; dconf write $LC/band1-gain 1.5; dconf write $LC/band1-q 0.8

# Band 2: 125Hz Bell -0.5dB Q0.9 — reduce bloat
dconf write $LC/band2-type "'Bell'"
dconf write $LC/band2-frequency 125.0; dconf write $LC/band2-gain -0.5; dconf write $LC/band2-q 0.9

# Band 3: 250Hz Bell -2.5dB Q1.1 — cabinet resonance cut
dconf write $LC/band3-type "'Bell'"
dconf write $LC/band3-frequency 250.0; dconf write $LC/band3-gain -2.5; dconf write $LC/band3-q 1.1

# Band 4: 500Hz Bell -1.5dB Q0.9 — low-mid clarity
dconf write $LC/band4-type "'Bell'"
dconf write $LC/band4-frequency 500.0; dconf write $LC/band4-gain -1.5; dconf write $LC/band4-q 0.9

# Band 5: 1kHz Bell 0dB Q1.0 — reference flat
dconf write $LC/band5-type "'Bell'"
dconf write $LC/band5-frequency 1000.0; dconf write $LC/band5-gain 0.0; dconf write $LC/band5-q 1.0

# Band 6: 2kHz Bell +1.5dB Q0.9 — presence/clarity
dconf write $LC/band6-type "'Bell'"
dconf write $LC/band6-frequency 2000.0; dconf write $LC/band6-gain 1.5; dconf write $LC/band6-q 0.9

# Band 7: 4kHz Bell +1.0dB Q1.0 — detail/air
dconf write $LC/band7-type "'Bell'"
dconf write $LC/band7-frequency 4000.0; dconf write $LC/band7-gain 1.0; dconf write $LC/band7-q 1.0

# Band 8: 8kHz Bell 0dB Q1.1 — neutral treble
dconf write $LC/band8-type "'Bell'"
dconf write $LC/band8-frequency 8000.0; dconf write $LC/band8-gain 0.0; dconf write $LC/band8-q 1.1

# Band 9: 16kHz Hi-shelf +0.5dB Q0.7 — sparkle
dconf write $LC/band9-type "'Hi-shelf'"
dconf write $LC/band9-frequency 16000.0; dconf write $LC/band9-gain 0.5; dconf write $LC/band9-q 0.7

# 5. Configure 4-band Multiband Compressor
MBC="/com/github/wwmm/easyeffects/streamoutputs/multibandcompressor/0"
dconf write $MBC/compressor-mode "'Modern'"
dconf write $MBC/enable-band1 true; dconf write $MBC/enable-band2 true
dconf write $MBC/enable-band3 true; dconf write $MBC/enable-band4 true
dconf write $MBC/split-frequency1 200.0; dconf write $MBC/split-frequency2 800.0
dconf write $MBC/split-frequency3 3000.0

# Band 0: 20-200Hz (Bass) — tight control
dconf write $MBC/attack-threshold0 -18.0; dconf write $MBC/attack-time0 10.0
dconf write $MBC/release-time0 150.0; dconf write $MBC/ratio0 2.0

# Band 1: 200-800Hz (Low-mids) — smooth muddy area
dconf write $MBC/attack-threshold1 -15.0; dconf write $MBC/attack-time1 15.0
dconf write $MBC/release-time1 120.0; dconf write $MBC/ratio1 1.5

# Band 2: 800-3000Hz (Mids) — vocal presence
dconf write $MBC/attack-threshold2 -12.0; dconf write $MBC/attack-time2 10.0
dconf write $MBC/release-time2 80.0; dconf write $MBC/ratio2 1.5

# Band 3: 3000Hz+ (Highs) — tame harshness
dconf write $MBC/attack-threshold3 -18.0; dconf write $MBC/attack-time3 5.0
dconf write $MBC/release-time3 60.0; dconf write $MBC/ratio3 2.0

# 6. Configure Limiter
LIM="/com/github/wwmm/easyeffects/streamoutputs/limiter/0"
dconf write $LIM/threshold -3.0; dconf write $LIM/attack 2.0
dconf write $LIM/release 10.0; dconf write $LIM/lookahead 5.0

# 7. Configure AutoGain
AG="/com/github/wwmm/easyeffects/streamoutputs/autogain/0"
dconf write $AG/target -20.0

echo "DSP chain configured. Restart EasyEffects:"
echo "  gdbus call --session --dest com.github.wwmm.easyeffects ... Ping"
```

## PipeWire Filter-Chain Alternative

If EasyEffects is broken, use a PipeWire filter-chain instead:

```
~/.config/pipewire/filter-chain.conf.d/10-eidolon-eq.conf
```

Creates an "EIDOLON Adaptive EQ" sink with 10 builtin biquad filters (bq_lowshelf + 8×bq_peaking + bq_highshelf).
Route: `easyeffects_sink → EIDOLON EQ → HDMI`

Adjust EQ bands at runtime:
```bash
pw-cli set-param eidolon-eq-filter port "{ eq_band_0:Gain = 2.0 }"
```
