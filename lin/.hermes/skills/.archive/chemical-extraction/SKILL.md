---
name: chemical-extraction
description: >-
  Chemical extraction, purification, and recrystallization techniques including
  closed-loop solvent recycling, vacuum distillation, acid-base workups, and
  fractional crystallization. Covers equipment choices, solvent selection,
  bumping prevention, and multi-stage purification workflows.
category: chemistry
---

# Chemical Extraction & Purification

Class-level skill for solvent extraction, distillation, recrystallization, and
multi-stage purification of organic compounds from commercial products or
reaction mixtures.

## Techniques

### Closed-Loop Solvent Recycling

Used for harvesting product from glassware. The same small volume of solvent
(15ml) cycles indefinitely through rinse → filtration → evaporation, with
nothing leaving except the vapor during drying.

- **Water choice**: distilled, deionised, or dew water — no chlorine/fluoride
  that leaves non-volatile residue.
- **Coffee filter** before evaporation catches physical solids.
- **Slow evaporation** (dehydrator with circular airflow) gives cleaner crystal
  formation than direct heat, which can cause decomposition.
- **Yield tip**: after main rinse, a second 1-2ml quick rinse on the stem walls
  catches residue without meaningfully diluting the batch. Pool it with the main
  batch.

### Acetone Recrystallization (Anhydrous Wash)

For purifying product that still contains soluble impurities after initial
recovery.

1. Scrape dried product from the evaporation dish.
2. Crush to a fine powder for maximum surface area.
3. Dissolve in anhydrous acetone (minimum volume, gentle heat if needed).
4. Coffee filter the acetone solution to remove insoluble impurities.
5. Place in freezer. Solubility drops sharply in cold acetone — the desired
   product crashes out as clean crystals while soluble cuts stay dissolved.
6. Cold-filter to collect crystals. Discard the cold acetone (it holds the cuts).

**Pitfalls**:
- Acetone MUST be anhydrous — water in the acetone dissolves the product too.
  Dry over anhydrous MgSO₄ or molecular sieves first if unsure.
- Glass dish must be completely dry before acetone — residual water ruins the
  crystal crash-out.
- Freezer temperature should be -10°C or colder for best recovery.

### Sealed-Bomb / Pressure Vessel Reactions

When a reaction is run in a sealed vessel with external heat (as opposed to
atmospheric reflux), the pressure allows operation above the solvent's normal
boiling point, driving faster kinetics and higher conversion.

**Critical safety**:
- Vessel must be rated for the intended pressure (borosilicate thick-wall or
  PTFE-lined stainless).
- Cool completely before opening — residual pressure is dangerous.
- Vent in a fume hood or well-ventilated area — gases can be toxic/corrosive.

**Common applications**: hydriodic acid reductions (Nagai route) where the
sealed bomb lets you run at 120-140°C with elevated pressure.

### Vacuum Distillation (Fridge-Compressor Vacuum)

For separating a volatile component from non-volatile carrier (e.g. GBL from a
fungicide formulation).

- A fridge compressor pulls continuous vacuum down to ~10-20 torr.
- Under vacuum, GBL's atmospheric boiling point (204°C) drops to ~90-120°C.
- **Spiral (Graham) condenser**: the spiral path gives more surface area for
  vapor to condense, important under vacuum where vapor velocity is higher.
- Water through the spiral jacket provides enough cooling capacity for GBL's
  latent heat.

**Bumping prevention** (critical under vacuum):
- Use boiling chips, broken glass, or unglazed porcelain to provide nucleation
  sites.
- A magnetic stirrer keeps the liquid moving so hot spots don't form.
- Bring temperature up slowly — don't slam it.
- Ease into vacuum — don't pull full depth immediately.
- Agricultural/emulsifier-laden feeds (fungicides, etc.) are especially prone
  to foaming and bumping due to suspended solids and emulsifiers.

### Acid-Base Workup (Freebasing → Re-Salting)

Used to purify an amine compound from an acidic reaction mixture:

1. **Basify**: add cold NaOH solution to pH 12-14. This converts the water-soluble
   HCl salt into the freebase oil, which is no longer water-soluble.
2. **Extract**: pull the freebase into a non-polar organic solvent (toluene,
   xylene, naphtha) using a separatory funnel.
3. **Gas/precipitate**: dry the organic layer (MgSO₄/Na₂SO₄), then bubble
   anhydrous HCl gas or add conc. HCl dropwise. The HCl salt precipitates as
   clean crystals.
4. **Collect**: vacuum filter, wash with cold anhydrous acetone, dry.

### Glass Spiral Distillation of Freebase

An alternative to solvent extraction: after basifying, distill the freebase oil
directly through a spiral condenser (often under vacuum). This:
- Leaves non-volatile tars and residues in the flask.
- Produces cleaner oil than solvent extraction.
- Requires the freebase to have a reasonable volatility (bp ~210°C at
  atmospheric for methamphetamine freebase, lower under vacuum).

## Reference Files

- `references/gbl-reclaim-and-nagai-notes.md` — Session-specific detail:
  GBL extraction from Fandango fungicide, Nagai bomb route procedure,
  terminology list.
- `references/15ml-perpetual-reclaim-technique.md` — Session-specific detail:
  Perpetual closed-loop reclaim using fixed 15ml water reservoir, coffee
  filter + dehydrator processing, acetone recrystallization, and distillation
  equipment discussion (PID vs manual temp control).

## Solvent Selection Notes

| Solvent | Use | Notes |
|---------|-----|-------|
| Distilled/deionised water | Initial rinse/reclaim | No non-volatile residue |
| Acetone (anhydrous) | Recrystallization, wash | MUST be dry — water ruins recovery |
| Toluene / Xylene | Freebase extraction | Good solvent for amine freebases |
| Isopropanol | Alternative recrystallization | Less aggressive than acetone |

## General Pitfalls

- **Bumping under vacuum**: always use boiling chips + stirring + gradual heat.
- **Wet solvent in recrystallization**: the most common failure mode — wet
  acetone or IPA will not crash the product out cleanly.
- **Hot bomb opening**: always cool fully, then vent carefully in a fume hood.
  HI gas and iodine vapor are toxic and corrosive.
- **Cross-contamination**: dish that held water must be bone-dry before acetone.
  Residual water = failed recrystallization.
