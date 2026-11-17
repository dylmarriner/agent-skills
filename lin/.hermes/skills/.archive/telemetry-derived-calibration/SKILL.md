---
name: telemetry-derived-calibration
description: Use when model tables must come from real measured data.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  category: engineering-data
  hermes:
    tags: [data-provenance, telemetry, calibration, datalogs, no-mock-data, physics-model]
    related_skills: [project-survey-and-orientation, codebase-audit, blueprint-audit-rollout]
---

# Telemetry-Derived Calibration

## When to Use

Use when a model, tune, config, or lookup table must be populated from measurements
rather than typed in: ECU/vehicle calibration from datalogs, performance models from
logged telemetry, any physics model whose constants are currently guesswork.

Also use when you are about to write a "starting value", "sensible default", or
"representative shape" into anything that drives real hardware or a real decision —
that impulse is the trigger.

This user's standing rule: **real data only**. No stub values, no mocks, no
"starting shape" numbers, nothing commented out or archived as a workaround. A
missing input is reported, never filled with a plausible number. A hand-authored
constant that feeds a real actuator is a defect, not a placeholder.

## Non-negotiable rules

1. **Two trust tiers, never mixed.** Published/authoritative constants (vendor spec
   deck, factory manual, datasheet) live in ONE file, tagged `source:` +
   `verified: true`. Every *tuneable* value comes from real logs in a SECOND file that
   is generated, not written by hand. Never let a constant masquerade as a measurement.
2. **A table that cannot be derived is absent.** No defaults, no fallbacks, no
   interpolation across a data gap. The model raises an error naming the channel to
   capture.
3. **Every derived value carries provenance**: source file, sha256, sample count,
   method string, coverage across the operating axis.
4. **Never hand-edit the generated artifact.** Its header says it is generated;
   regenerate it after new logs.
5. **Say which numbers are anchored and which are not.** When no measurement anchors
   the absolute scale, present deltas between configurations as the trustworthy
   result and mark the absolute values unvalidated in the output itself.

## Procedure

### 1. Find whether real data exists before designing anything

Search the repo and the user's machine for existing recordings (`data/`, `logs/`,
`*.csv`, `*.csv.gz`, `*.bin`). Also check whether the source system serves the real
recordings over an API — vendor telemetry sites hand them out from a JSON endpoint,
and the browser page's own network activity reveals the URL. Download the real file
and record its checksum next to it.

If no real data exists anywhere: stop and specify exactly what to capture (which
channels, which operating points, minimum rate). Do NOT author placeholder tables to
"unblock" the model — that is the failure this skill exists to prevent.

### 2. Write ONE importer that sniffs the real format

Never invent a format. Point it at what the real tools actually write and keep the
header text as the unit source. Support gzip (vendor tools compress logs). Detect the
header row instead of assuming line 1.

### 3. One derivation function per table

Each returns values + axis + n_samples + method + sources + coverage. Aggregate with
a **median per operating bin**, not a mean: real logs carry spikes, shift transients
and junk cells.

### 4. Gate every derivation on data quality

Required channels present, minimum total samples, minimum samples per bin, and a
sample-rate/quantisation check for anything requiring differentiation. On failure,
raise a named error quoting the real numbers and the channel to log. Run
`scripts/log_probe.py` first on any new log set — it reports channel resolution,
sample rate and which derivations are supportable.

### 5. Generate the derived artifact, then make the model depend on it

Model code loads ONLY the generated file, and raises if a required table is missing,
listing the reason per missing table. Add a test that feeds it an empty tables block
and asserts the refusal fires.

### 6. Calibrate free constants against real anchors, not shapes

Fit at most as many constants as there are real anchors. An over-determined fit
produces physically impossible coefficients (negative friction, efficiency outside
range) that still pass arithmetic. When the model cannot reproduce the measured
curve's shape, either let the *data* carry the shape (fix the measured input tables)
or model the output **relative to a measured reference curve** so the absolute scale
stays anchored to a measurement.

### 7. Validate, then label

Compare model output against the measured anchor **at the same operating point** —
comparing a peak against a measurement taken elsewhere is not validation. Restrict
simulation/interpolation to the operating range the real data covers. Print, in the
summary: which logs the tables came from, the covered range, and whether the absolute
scale is anchored or unvalidated.

## Pitfalls

- **Substring channel matching picks the wrong column.** Real headers place
  `MAF Voltage (V)` before `Mass Airflow (g/s)`; a "contains `maf`" rule silently feeds
  volts into an airflow model and every downstream number is wrong but plausible.
  Match ordered patterns, specific first, and keep the matched header text for unit
  decisions.
- **Real logs are encoding-hostile.** Degree signs arrive mangled, bracketed unit text
  (`(RPM)`, `(mph)`, `(°F)`) must be stripped before matching, and metadata hides in a
  trailing column. Normalise the header first; skip unparseable cells instead of
  aborting the file.
- **Unit sloppiness is invisible until the output magnitude is checked.**
  `force x speed` is watts — a module documenting kW that receives watts reports
  1000x high, and derives torque 1000x high from that. Fix it where all callers route
  through, and assert the magnitude is plausible, not merely the type.
- **Validate a derived constant against an independent published value before trusting
  the pipeline.** A derived ratio matching the spec sheet validates radius, speed
  channel, units and grouping in one shot; a mismatch means the grouping bands or an
  assumed constant is wrong.
- **Sample rate decides which derivations are legal.** A speed channel quantised to one
  unit at 10 Hz yields acceleration quantisation of several m/s2; torque from
  differentiating that is noise with a decimal point. Gate on effective sample rate and
  refuse — real dyno pulls log wheel speed at 20-50 Hz for exactly this reason.
- **Silently mixing data sources produces confident nonsense.** Airflow tables measured
  on a modified vehicle plus a torque anchor from a stock spec sheet yields an absurd
  absolute curve. Anchor and tables must come from the same configuration, or the
  mismatch is printed on every result.
- **Flag every remaining assumption in-band.** Anything still assumed (a per-gear trim
  no log covers, a drivetrain loss figure) is listed in the model's own output with the
  specific log that would remove it — never buried in a comment.

See `references/derivation-gates.md` for the channel/rate/coverage gate table and the
refusal-message pattern, `references/engineering-model-notes.md` for measured-anchor
physics modelling notes, and run `scripts/log_probe.py LOG` to get the channel list,
resolution and supportable-derivation verdict for any new log before you write code.
