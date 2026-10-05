---
name: explain-plan
description: Explain or troubleshoot a plan the optimizer produced from a HAEO diagnostics export — why the battery charged or discharged when it did, why power was or was not exported, why solar was curtailed, why a plan looks wrong or wasteful, or why cost is higher than expected. Use whenever someone asks "why did the optimizer do X", "why didn't it do Y", or reports that HAEO is behaving oddly. Also covers adding new analysis modules to the diag CLI.
---

# Explaining an optimizer plan

The optimizer minimizes total cost across the **whole horizon**, so almost every decision that looks wrong in isolation is being driven by something elsewhere in time.
Explaining a plan means finding that driver and showing it, not describing what the plan does.

The raw material is a diagnostics export: Settings → Devices & Services → HAEO → Download Diagnostics.
Save it somewhere scratch, or as `tests/scenarios/<name>/scenario.json` if it should become a regression test — see the `scenarios` skill.

## First, pin down the question

People describe optimizer behavior loosely. Before analyzing anything, establish four things, from the report if possible and by asking if not:

1. **Which element** — the battery, the grid connection, solar, a specific load.
2. **Which interval** — a clock time, or the phrase that identifies it ("this morning", "the price spike").
3. **What it did** — the observed decision.
4. **What they expected instead** — this is the one people leave out, and it is the one that makes the question answerable.

"Why is it charging from the grid at 6pm?" is not yet answerable.
"Why is it charging from the grid at 6pm at 45c when it could wait for solar tomorrow morning?" names a specific alternative you can price.

The question is nearly always one of:

- **Why did it do X?** — find the binding constraint or the price comparison that made X optimal.
- **Why didn't it do Y?** — price Y and show it is worse, or find the constraint that forbids it.
- **The plan is wrong** — usually bad input data rather than a bad decision. Check the inputs first.

## What is in the export

| Section            | Contents                                                                       |
| ------------------ | ------------------------------------------------------------------------------ |
| `config.json`      | Element configuration and hub tiers — what was set up                          |
| `environment.json` | Timestamps and timezone — `optimization_start_time` is "now" for that plan     |
| `inputs.json`      | Raw Home Assistant sensor states the optimizer read                            |
| `outputs.json`     | The plan: every entity's `state` plus a `forecast` series, including all duals |

`outputs.json` is the record of what the optimizer actually decided.
Everything needed to explain a decision is in there — dispatch, prices, state of charge, and shadow prices, all as time series.

## Reproduce before explaining

```bash
uv run diag --file <dir>            # re-solve and print the plan
uv run diag --file <dir> --compare  # stored plan vs fresh solve, differences highlighted
```

If `--compare` shows meaningful divergence, the plan in Home Assistant was produced from different inputs than the ones captured, and the question may really be about staleness rather than about the optimizer's reasoning.
Small drift in later intervals is normal.

## The core question: forced, or chosen?

Every decision is one or the other, and the shadow prices tell you which.

A shadow price is the marginal value of relaxing a constraint by one unit, in \$/kWh.
**Zero means the constraint is slack; non-zero means it is binding.**

- **Some limit dual is non-zero** → the optimizer was **forced**. That constraint is the answer: it wanted more and could not have it. The magnitude says how much the next kWh of headroom would have been worth.
- **All limit duals are zero** → the optimizer **chose**. Nothing physical was in the way, so the decision was economic, and the explanation is a price comparison.

The power balance dual at a node is the marginal value of energy there and then.
Compare it against import and export prices to see what set the decision.

`diag` answers this directly:

```bash
uv run diag -f <dir> -a binding          # every dual, grouped by what it means
uv run diag -f <dir> -a binding:0.01     # ignore duals below 1c/kWh
```

It splits the constraints three ways:

- **Capacity limits reached** — power and state-of-charge limits that bound. These are the forced decisions, and this is the section that answers "why couldn't it".
- **Forecast limits** — load and generation limits bind by construction, so their duals say what an extra kWh of that resource would have been worth, not that a choice was denied.
- **Marginal energy value** — the balance duals, which is what power was worth at each point.

When the capacity section is empty, nothing physical constrained the plan and the explanation is entirely a price comparison.

Then line the relevant series up against each other:

```bash
uv run diag -f <dir> -a series:'discharge_power|export_price'
uv run diag -f <dir> -a series:shadow
uv run diag -f <dir> -a binding -a series:soc   # analyses compose
```

**Not every limit publishes a dual.** Battery charge and discharge power limits, for example, are enforced on the connection elements and may have no `*_shadow_price` sensor in a given topology.
`binding` prints a reminder of this; where a flow sits exactly at its configured maximum with no dual to match, compare it against its `number.*` limit value directly rather than assuming the limit was slack.

## Worked example

In `tests/scenarios/scenario3` the battery sits at 1 kW (serving load only) all morning, then discharges at its cap and exports 18.2 kW for four intervals from 09:35, then stops.
Columns below are abbreviated entity ids, as the helper prints them:

```
  time  export_price  discharge_power  switchboard_power_  grid_max_export_po
 09:30        0.2200           1.0000              0.2200              0.0000
 09:35        0.2600          19.4000              0.2600              0.0000
 09:40        0.2700          19.4000              0.2700              0.0000
 09:45        0.3500          19.4000              0.3500              0.0000
 09:50        0.3100          19.4000              0.3100              0.0000
 09:55        0.2000           1.0000              0.2200              0.0000
```

Every limit dual is zero, so nothing was forced — this was a choice.
The node balance dual never falls below 0.22, which is the opportunity cost of holding stored energy rather than selling it now.
Export happens exactly in the intervals where the export price beats that floor, and stops when it does not.

`uv run diag -f tests/scenarios/scenario3 -a binding` reports no capacity limits reached, which is what licenses reading this as an economic choice.

Confirm rather than assert. Copy the scenario, flatten the export price, re-solve:

```bash
cp -r tests/scenarios/scenario3 /tmp/probe
# set every feed-in per_kwh in /tmp/probe/inputs.json to 0.05
uv run diag --file /tmp/probe/
```

The discharge burst disappears entirely and the battery holds charge.
That is a decisive answer, not an interpretation.

## Perturbation is the strongest tool available

Any hypothesis of the form "it did X because of Y" is testable: copy the scenario, change Y alone, re-solve, see whether X changes.
Use it whenever the price story is not obvious. Useful perturbations:

| Hypothesis                        | Change                                         |
| --------------------------------- | ---------------------------------------------- |
| Driven by an export or spot price | Flatten that price series                      |
| Held back by a power limit        | Raise the limit in `config.json`               |
| Driven by a later opportunity     | Shorten the horizon in `config.json` tiers     |
| Caused by a forecast              | Flatten or zero that forecast in `inputs.json` |
| Caused by round-trip losses       | Set efficiencies to 100                        |

Change one thing at a time, and keep the original directory untouched for comparison.

## Question to starting point

| Question                             | Look at                                                                        |
| ------------------------------------ | ------------------------------------------------------------------------------ |
| Why charge / discharge now?          | Node balance dual against import and export prices across the whole horizon    |
| Why not charge from cheap power?     | Charge power limit, SoC max dual, round-trip efficiency, whether SoC is capped |
| Why export instead of storing?       | Export price against the node balance dual floor                               |
| Why import while solar is available? | Solar forecast series, curtailment switch, inverter limits, the topology       |
| Why curtail solar?                   | Export price sign, export limit dual, whether load and battery can absorb it   |
| Why is SoC pinned?                   | `soc_min` / `soc_max` duals and the configured min and max percentages         |
| Why is cost higher than expected?    | `sensor.optimizer_cost`, then per-element cost and revenue outputs             |
| Why does the plan keep changing?     | Input forecast churn — compare consecutive exports, not one in isolation       |

## When it is not the optimizer

Most "the optimizer is wrong" reports are input problems. Check these before analyzing duals:

- **Stale or missing forecast** — an entity in `inputs.json` that is `unknown`, `unavailable`, or whose forecast ended before the horizon does.
- **Unit mismatch** — a sensor publishing W where kW is expected, or a price in c/kWh rather than \$/kWh. Values off by 1000 or 100 are the tell.
- **Horizon too short** — the plan cannot see the opportunity the user is thinking of. Compare the horizon length against the interval they mention.
- **Limits misconfigured** — a driven limit sensor reporting something implausible.
- **Policy rules** — with policies configured, flows are priced by source and destination, and a flow may be effectively barred by tagging. See `docs/modeling/tagged-power.md` and the `model` skill.
- **Degenerate optimum** — when several plans cost the same, the time-preference secondary objective breaks the tie. If two plans differ but cost the same, the choice between them carries no economic meaning and should be explained that way.

## Extending diag

`diag` is the diagnosis tool, and it is meant to grow. **If answering a question required analysis that diag could not do, add that analysis to diag rather than doing it ad hoc.** The next person asking a similar question then gets it for free, and the reasoning becomes reproducible instead of living in a chat log.

Analyses are modules under `tools/diag/analysis/`, each answering one question and rendering the answer as text a human or an agent reads directly.

Add one by creating a module there that defines `NAME`, `HELP`, and `run(outputs, config, argument) -> str`, importing it in `analysis/__init__.py`, adding it to `ANALYSES`, and adding a case to `tests/test_diag_analysis.py`.

Guidelines that keep them useful:

- **One question per module.** If the help text needs "and", it is two analyses.
- **Lead with the finding, then the numbers.** The caller wants a conclusion they can act on, not a data dump they have to interpret.
- **Say what an absence means.** "No capacity limit binds" is a finding worth stating explicitly, not an empty section.
- **Do not overstate.** Distinguish constraints that bind by construction from ones that genuinely blocked a choice, as `binding` does.
- **Read the export, not a re-solved network**, so the analysis describes the plan that actually ran and works with `--outputs-only`.
- Analyses inherit the import boundary: `tools/diag/**` may only use `custom_components.haeo.core`, `numpy`, and `tabulate`.

Signs an analysis is worth adding: you wrote a throwaway script to answer it, you have answered the same shape of question twice, or the answer required cross-referencing several entities by hand.

## Answering well

Lead with the driver, not the description.
State whether the decision was forced or chosen, name the constraint or the price comparison responsible, and give the numbers.
Say what would have had to be different for the plan to change — that is usually what the person actually wants to know.

If the behavior turns out to be a genuine bug, turn the export into a scenario so it stays fixed, following the `scenarios` skill.
