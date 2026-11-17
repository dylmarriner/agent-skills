# Redmi Note 13 5G — Hardware Test Points & Phone Opening

## Device Identity

| Field | Value |
|-------|-------|
| Model | Redmi Note 13 5G |
| Codename | gold / iron |
| Chipset | MediaTek Dimensity 6080 (MT6833V) |
| OS | HyperOS (MIUI 14) |
| HW Revision | ca00 |
| Region | gl (Global) |

## Opening the Phone

1. **Heat** back edges with hairdryer/heat gun at ~80°C for 2 minutes (plastic back with clips + adhesive)
2. **Suction cup** on bottom third of back cover, pull up to create gap
3. **Pry tool** in gap, slide around perimeter — clip by clip
4. **Remove** all Phillips screws from midframe
5. **Disconnect battery FIRST** — orange flex cable near bottom of battery

## Test Point Locations

The test points are near the battery connector area on the motherboard:

- Two small gold circular pads
- Sometimes labeled **KCOLO** or **KCOL0**
- Often unmarked — look for bare gold circles
- One pad is GND (larger pad or any metal shield works as ground)
- The other is the test point (TP)

### Procedure

1. Open phone, disconnect battery
2. Locate test points near battery connector
3. Bridge both pads with tweezers
4. **While bridged**, plug USB cable
5. Device enters BROM mode (0e8d:2000)
6. Release short after device detected on USB
7. Run mtkclient

## Critical Note

**Test points bypass the button combo, NOT the SLA authentication.** Dimensity 6080 SLA will still block free mtkclient even from test-point BROM. The phone must still pass the RSA challenge-response against a valid key. Test points are useful when:

- Key combos don't work (boot menu keeps appearing instead of BROM)
- The device is in a boot loop and can't be powered off properly

They do NOT help with SLA bypass unless you already have a valid key added to `brom_sla_keys`.

## Power-Off Timing (Xiaomi)

- Hold Power **10 seconds** max
- Release the MOMENT the screen goes black
- Holding 15+ seconds triggers reboot, not power-off
- If phone turns back on after holding Power, you held too long
