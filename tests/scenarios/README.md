# HAEO scenario tests

Scenario tests run whole optimizations from real Home Assistant data and compare the results with a snapshot.
The [testing guide](../../docs/developer-guide/testing.md#scenario-testing) explains where they fit, and the `scenarios` agent skill in `.agents/skills/scenarios/` has the full workflow.

## Adding a scenario from diagnostics

1. In Home Assistant, open Settings → Devices & Services → HAEO → Download Diagnostics.
2. Create a folder whose name starts with `scenario`, such as `tests/scenarios/scenario_evening_peak/`.
3. Save the download in it as `scenario.json`.
4. Run the scenario suite twice with `uv run pytest -m scenario`.
    The first run splits `scenario.json` into the four files below and deletes it; the second runs the new scenario and writes `outputs.json`.
5. Review the outputs, run `uv run check --fix` so Prettier formats the new files, and commit.

## Files

```
scenario_name/
├── config.json       # Hub config entry data, with element subentries under participants
├── environment.json  # HA and HAEO versions, time zone, and the captured timestamps
├── inputs.json       # Input entity states with attributes and forecasts
├── outputs.json      # Expected output sensor states (the snapshot)
└── visualizations/   # Network topology and optimization plan SVGs
```

`config.json` holds the hub's sections, such as `common` with its `horizon_preset`, and each element's fields in the same sections its subentry stores.
Copy an existing scenario's config rather than writing one from scratch.

`environment.json`'s `optimization_start_time` is the time the test freezes to.

`test_scenarios.py` runs every folder matching `scenario*/` that holds all four JSON files.
A folder without `outputs.json` is skipped, so a hand-written scenario needs an `outputs.json` holding `{}` before its first `--snapshot-update` run.

## Running

```bash
# Every scenario, as the scenario gate in uv run check and CI run them
uv run pytest -m scenario

# One scenario
uv run pytest -m scenario -k scenario1

# Rewrite outputs.json after an intended change
uv run pytest -m scenario --snapshot-update
```

The visualizations are rendered through the forecast card bundle, which `uv run check` builds; when running pytest directly, build it once with `npm --prefix frontend/haeo-forecast-card ci` and `npm --prefix frontend/haeo-forecast-card run build`.

## Filtering a state dump

`filter_states.py` extracts the states of selected entities from a Home Assistant instance or a saved state dump:

```bash
./tests/scenarios/filter_states.py http://ha.local:8123 -o states.json sensor.battery sensor.solar
./tests/scenarios/filter_states.py states.json -o filtered.json --patterns-from-file sensors.txt
```
