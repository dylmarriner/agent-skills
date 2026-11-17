# Derivation gates: channels, rates, coverage

Every gate exists so a wrong-but-plausible number cannot reach a real actuator.
Raise on failure; never substitute a default.

## Gate table

| Derivation | Required channels | Aggregation | Minimum gate |
|---|---|---|---|
| Volumetric efficiency | RPM, mass airflow, manifold pressure, intake/charge temp | median per operating bin, high-load samples only | >=20 high-load samples; >=3 samples per bin |
| Manifold/boost target | RPM, manifold pressure, + load or pedal | median per bin | pull must exist (samples above the load/pedal threshold) |
| Fuel target | RPM, lambda or wideband AFR, + load | median per bin, exclude overrun (lean > ~16 AFR) | pull must exist |
| Ignition/command tables | RPM, spark advance (+ knock retard for the margin channel) | median per bin | pull must exist |
| Actuator duty tables | RPM, duty channel | median per bin | pull must exist |
| Ratios (gated through the driveline) | RPM, road speed | cluster the per-sample ratio, keep clusters with enough samples | >=10 moving samples; report only clusters >= threshold samples |
| Torque / power from a trace | RPM, road speed, time | median per bin, after smoothing | see rate gate below |

## Sample-rate gate for differentiated quantities

Acceleration is `d(speed)/dt`, so its resolution is the speed channel's least
significant step divided by the sample interval. A channel quantised to one unit at
10 Hz gives acceleration quantisation of several m/s2 — unusable for torque, even
though every individual number looks fine.

Rule: compute the effective usable rate from the surviving samples
(`n_surviving / time_span`) and refuse below ~15-20 Hz, naming the required logging
rate in the error. Real dyno pulls log wheel speed at 20-50 Hz.

Refusal-message pattern (quote the real numbers, name the fix):

```
"{log}: {rate:.1f} Hz usable samples ({n} over {span:.1f} s) cannot resolve
 acceleration - log a single-gear pull at 20 Hz or faster before this table is
 trustworthy"
```

## Compute the gate, do not assert it

Return `coverage = populated_bins / total_bins` and `n_samples` from every derivation
and store both in the generated artifact. Emit a per-table `trustworthy` boolean from
them so downstream code and the user can see which tables are thin. Thin tables are
reported, not silently used as if they were full.

## Gear/ratio clustering recipe

1. Per sample: `total_ratio = rpm * 2*pi*r / (60 * v)` with `v` in m/s.
2. Drop samples below a moving-speed floor and implausible values.
3. Sort, then split into clusters at a ~2% relative gap.
4. Keep clusters with at least the minimum sample count; report each cluster's median.
5. Do NOT divide by an assumed final-drive constant to "name" the gear unless the
   constant is published for the exact variant — report the observed totals and let the
   published constant be the cross-check.

A single-gear street log legitimately yields ONE ratio. That is the honest answer; do
not manufacture the missing gears.
