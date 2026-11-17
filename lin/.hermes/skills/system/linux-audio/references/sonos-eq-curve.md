# Sonos Playbar + Sub EQ Curve (EasyEffects)

## Audio Path
**PC → HDMI → TV → Optical (S/PDIF) → Sonos Playbar + Sub**

The TV passes stereo PCM from HDMI to optical. The Playbar handles the front soundstage; the Sub handles everything below ~80Hz wirelessly.

## Studio Reference Curve (10-band Parametric)

Loaded as preset `studio-reference` in EasyEffects.

| Band | Freq | Gain | Type | Q | Purpose |
|------|------|------|------|---|---------|
| 0 | 31 Hz | +2.0 dB | Lo-shelf | 0.7 | Sub-bass foundation — Sub handles this beautifully |
| 1 | 63 Hz | +1.5 dB | Bell | 0.8 | Sub-to-Playbar transition — warmth without bloat |
| 2 | 125 Hz | -0.5 dB | Bell | 0.9 | Trim slight boxiness from optical path |
| 3 | 250 Hz | -2.5 dB | Bell | 1.1 | **Key cut** — Playbar's cabinet resonance zone |
| 4 | 500 Hz | -1.5 dB | Bell | 0.9 | Clean up low-mid congestion |
| 5 | 1 kHz | 0 dB | Bell | 1.0 | Reference flat — vocals, instruments |
| 6 | 2 kHz | +1.5 dB | Bell | 0.9 | Presence — vocals cut through |
| 7 | 4 kHz | +1.0 dB | Bell | 1.0 | Detail — cymbals, strings, air |
| 8 | 8 kHz | 0 dB | Bell | 1.1 | Neutral treble — no harshness |
| 9 | 16 kHz | +0.5 dB | Hi-shelf | 0.7 | Gentle sparkle at the top |

### Processing Chain
**Equalizer → Multiband Compressor → Limiter → AutoGain**

Output gain: -0.5dB (prevents clipping from low-end boosts).

## AI Adaptive EQ Modulations

The IntelligentEq engine modulates the base curve by up to +/-3dB per band based on real-time spectral analysis:

### Algorithm
1. Normalize 10 band energies by dividing by total energy
2. Maintain rolling EMAs: short-term (~0.5s), long-term (~3s)
3. Convert long-term energy to dB relative to the 1kHz band (band 5)
4. Compare against target relative levels
5. If deviation > 1.5dB, apply gentle correction (-error * 0.35)
6. If deviation <= 1.5dB, apply slight opposite correction (error * 0.15) to preserve mix
7. Smooth across adjacent bands (0.3 weight)
8. Attack/release envelope: ~2s attack, ~5s release

### Target Relative Levels (dB re: 1kHz)
| Freq | Target | Rationale |
|------|--------|-----------|
| 31 | +2.0 | Sub should sit slightly above 1kHz |
| 63 | +1.0 | Bass fullness |
| 125 | -2.0 | Below 1kHz — reduce mud |
| 250 | -3.0 | Below 1kHz — clarity zone |
| 500 | -1.0 | Slightly below |
| 1k | 0.0 | Reference anchor |
| 2k | +1.0 | Presence forward |
| 4k | +0.5 | Detail without sibilance |
| 8k | -1.0 | Below 1kHz — avoid harshness |
| 16k | -2.0 | Below — natural rolloff |

## PipeWire Filter-Chain Equivalent

When EasyEffects is unavailable, use this pw-cli filter-chain config (see `templates/10-eq-filter-chain.conf`).

## Troubleshooting

- **No sound**: Check WirePlumber is running, then verify `pw-link` shows the routing chain
- **Audio skips**: Reduce FFT size from 2048 to 1024 or increase capture buffer
- **EQ not updating**: The filter-chain node must exist — if PipeWire restarted, recreate null sink and links
- **Bass too weak**: Increase Sub volume in Sonos app before touching sub-80Hz EQ bands
- **Sounds compressed**: Bypass AutoGain in EasyEffects
