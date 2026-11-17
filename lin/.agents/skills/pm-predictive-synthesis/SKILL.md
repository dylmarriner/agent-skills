---
name: pm-predictive-synthesis
description: Forecast project delivery or identify emerging schedule and dependency risks from real historical data. Use for delivery ranges, deadline confidence, scenario comparisons, or evidence-based early warnings.
---

# Predictive project synthesis

Define the decision before choosing a model: completion date, chance of meeting a deadline, capacity requirement, or leading risk. Never manufacture a probability to make a status report look analytical.

1. Inspect the source data and its units: completed items per period, cycle times, scope remaining, work calendars, and blocked dependencies. State the observation window and missing records. Do not treat story points from different teams as interchangeable output.
2. Establish a simple baseline. Check whether the history represents the coming work; separate changes in staffing, scope, process, and item size. Zero-throughput periods can be real observations, not automatically bad data.
3. When sufficient comparable history exists, calculate a forecast using actual computation. For a throughput bootstrap, repeatedly sample complete historical periods until remaining scope is covered; retain zero periods, enforce a finite simulation horizon, and report unfinished runs. Fix and record the random seed and run count.
4. Report a range and useful percentiles, the deadline probability if calculated, and sensitivity to scope or capacity changes. Include the baseline, assumptions, and data limitations. Simulation output is modeled evidence, not a delivery commitment.
5. Check simple invariants: zero remaining scope needs zero work periods; more remaining scope cannot improve completion under the same sampled trajectory; a deadline probability stays between zero and one. Test all-zero history explicitly.

If the data cannot support a numerical forecast, deliver a qualitative risk assessment and identify the missing evidence. End with the decision implication, controllable drivers, and the next refresh trigger.

Conceptual inspiration: [Skillbook Academy's project-manager competencies](https://skillbookacademy.com/resources/ai-powered-project-manager-skills/). Independently authored; not an official Skillbook package.
