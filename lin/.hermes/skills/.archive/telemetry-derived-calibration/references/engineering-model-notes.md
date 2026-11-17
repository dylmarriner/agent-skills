# Modelling outputs against a measured anchor

Notes for physics/engineering models whose input tables were derived from real logs.

## Chain of the model, in the order the physics runs

1. Manifold conditions: pressure ratio from gauge boost against ambient; charge density
   from absolute pressure and charge temperature.
2. Airflow: `VE(rpm) * displacement * (rpm/120) * density`. With VE derived from
   measured airflow the model reproduces the measured mass flow by construction —
   check that, it is the cheapest end-to-end check of the derivation.
3. Fuel: airflow / target AFR; fuel energy = mass flow * lower heating value.
4. Work: indicated output = efficiency * fuel energy, converted to torque at shaft speed.
5. Losses: subtract friction/pumping. A single linear loss term CANNOT satisfy both
   "peak torque at low rpm" and "peak power at mid rpm" while torque falls to redline —
   if you need both, the shape must come from the measured input tables, or add a term
   whose ceiling and upgrade path are documented.
6. Limits: per-gear caps, actuator ceilings, and any envelope read from the data.

VE above 1.0 is a real outcome when the logged charge temperature understates the
actual post-cooler temperature: the derived VE absorbs the density error. Keep it and
say so in the method string rather than clamping to 1.

## Anchoring an absolute scale

- Fit ONE free efficiency constant to ONE measured anchor (the mid-point of the real
  measurements), and record which point it was fitted to.
- Fitting N constants to N points reproduces the points exactly and yields nonsense
  coefficients (negative loss terms, absurd intercepts). If the fit needs more than a
  couple of constants, the model's shape is wrong, not under-parameterised.
- **Relative model when a measured curve exists**: `output = measured_reference(axis) *
  (input_now / input_at_reference) * derating factors`. The absolute scale stays
  anchored to the measurement, and edits to the configuration only move you relative to
  it. This cannot produce a physically absurd absolute value.
- When there is no measured curve, anchor to a published figure, and mark the absolute
  output unvalidated in every summary line.

## Gating a run to the covered range

Start any simulated run at the bottom of the range the real data covers rather than at
a nominal low figure — outside the covered range you are extrapolating, and
interpolation clamps to the end points, which silently invents a flat region. Report
the covered range on every result.

## Input-channel caveats that break the model silently

- A logged "throttle position" channel may cap well below 100% while the pedal channel
  reaches ~99%. Gate "full load" samples on load and/or pedal, and treat plate-angle
  channels as advisory.
- Shift transients and junk cells poison differentiation: median-filter the trace
  before differentiating, and guard spikes with a robust threshold derived from the
  data rather than a fixed constant.
- A trace spanning a gear change yields per-sample ratios in two clusters; compute
  torque only within one cluster or the recovered torque is fiction.
- Enforce that the configuration's anchor and its input tables describe the same
  vehicle/configuration; print the mismatch loudly when they do not.

## Calibration knobs to leave in place

Leave a named, documented knob for the physical world rather than hard-coding the
ideal: test mass, traction coefficient, drivetrain loss, and any temperature-based
penalty. Real hardware reads a few percent off, and the knob is what lets the user
reconcile the model with their own measured sheet.
