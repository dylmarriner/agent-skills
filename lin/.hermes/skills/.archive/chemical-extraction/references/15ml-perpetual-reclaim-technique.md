# 15ml Closed-Loop Perpetual Reclaim Technique

Session reference: 2026-07-15 on lin (shared chemistry/distillation conversation).

## Overview

A closed-loop reclaim system using a fixed small volume of water (15ml) that
cycles indefinitely through use → rinse → filter → dehydrate → reuse, with
no dilution and no water lost (except as vapor during drying).

## The Technique

### Setup
- **Reservoir:** 15ml distilled/deionised/dew water in a sealed jar
- **Use cycle:** Rinse pipe/stem with the same 15ml after each session
- **Duration:** The same 15ml cycles for months without replacement
- **Filter step:** Only when it's time to reclaim the accumulated product

### Reclaim process
1. Coffee filter the 15ml → removes physical solids and carbonized residue
2. Dehydrate the filtered liquid → slow evaporation with circular airflow
   (food dehydrator or warm airflow setup)
3. Scrape dried product from dish
4. (Optional) Acetone recrystallization for cleaner end product:
   - Crush dried product to fine powder
   - Dissolve in minimum anhydrous acetone
   - Coffee filter acetone solution to remove insolubles
   - Freeze crash (-10°C+) → clean crystals precipitate
   - Cold-filter to collect product
   - Discard cold acetone (carries the soluble cuts away)

### Why it works
- **No dilution:** The 15ml is a fixed closed loop — nothing leaves it except
  vapor during drying, and nothing new enters it
- **No concentration overload:** Each rinse adds only micrograms from stem
  residue. Months of buildup before it's worth processing
- **Coffee filter removes tars:** The black carbonized buildup that would
  contaminate the final product gets filtered out before dehydration

## Distillation Equipment Discussion

### Solvent recovery still setup
- **Heating:** A simple hotplate with a knob (no PID controller)
- **Temp monitoring:** Infrared temp gun aimed at the boiling flask
- **Condenser:** Spiral (Graham) style — coiled inner tube for vapor path
- **Issue:** No thermocouple in the flask means reactive temp control only
- **Key problem:** With manual knob + temp gun, you can't hold a steady boil.
  The temp fluctuates as thermal mass overshoots and you correct after the fact

### PID vs Manual knob
- PID controller: holds temp within ±1°C of setpoint automatically
- Manual knob: operator sees temp dropping, turns up, 30s later it's 20°C
  over target, turns down, 30s later it's 10°C under — thermal oscillation
- For GBL distillation: this matters less (boiling point 90-120°C under
  vacuum, decomposition temperature is much higher)
- For fraction-sensitive distillations: PID is essential

### Ideal upgrade path
1. K-type thermocouple probe (fits into the distillation head or flask neck)
2. $40-60 PID controller (Inkbird, Auber, or similar)
3. SSR (solid state relay) to handle the heater power
4. Wire PID → SSR → hotplate. Setpoint goes into PID, PID controls power

## Pitfalls
- **Water quality matters** — tap water has chlorine/fluoride that
  concentrates as a non-volatile residue. Use distilled, deionised, or dew
  water only
- **The dehydrator airflow must be clean** — dust in the air will settle
  into the drying product. Use a HEPA filter or clean-room environment
- **Don't disc the coffee filter into the dry product** — scrape cleanly
  from the glass, not the paper
- **Wet acetone recrystallization fails** — if the acetone absorbed water
  from the air, the product won't crash out. Keep acetone anhydrous
- **15ml evaporates slowly if surface area is small** — use a wide, flat
  dish to maximize evaporation surface, not a narrow beaker
