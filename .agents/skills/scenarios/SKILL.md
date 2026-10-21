---
name: scenarios
description: End-to-end scenario tests in tests/scenarios/ — creating a scenario from a user's diagnostics download, running them, updating outputs.json snapshots, and reading a scenario diff. Use when a scenario test fails, when reproducing a user-reported optimization result, or when adding a regression scenario.
---

# Scenario testing

Scenario tests are end-to-end integration tests with realistic configurations and time-frozen states.

## Structure

```
tests/scenarios/
├── test_scenarios.py         # Centralized parameterized test runner
├── conftest.py               # Shared fixtures
├── syrupy_json_extension.py  # Snapshot format
├── visualization.py          # Debugging visualizations
└── scenario*/
    ├── config.json           # Hub and element configuration
    ├── environment.json      # Timestamp for time freezing
    ├── inputs.json           # HA sensor states to inject
    └── outputs.json          # Expected sensor outputs (snapshot)
```

## Auto-discovery

Test runner automatically discovers all `scenario*/` folders using `Path.glob("scenario*/")`.
No registration needed - just create a new folder.

## Scenario files

### config.json

Hub configuration and element participants:

```json
{
  "tier_1_count": 12,
  "tier_1_duration": 5,
  "participants": {
    "Battery": {
      "element_type": "battery",
      "name": "Battery"
    }
  }
}
```

### environment.json

Captured runtime context. The `optimization_start_time` is used as the test's freeze timestamp:

```json
{
  "ha_version": "2024.1.0",
  "haeo_version": "0.1.0",
  "timezone": "UTC",
  "diagnostic_request_time": "2024-01-15T12:00:00+00:00",
  "diagnostic_target_time": null,
  "optimization_start_time": "2024-01-15T12:00:00+00:00",
  "optimization_end_time": "2024-01-15T12:00:00+00:00",
  "horizon_start": "2024-01-15T12:00:00+00:00"
}
```

### inputs.json

Home Assistant sensor states to inject before optimization.
Array of state objects with keys:

- `entity_id`: Entity ID string
- `state`: State value as string
- `attributes`: Object with `unit_of_measurement`, `forecast`, etc.

```json
[
  {
    "entity_id": "sensor.solar_power",
    "state": "3500",
    "attributes": {
      "unit_of_measurement": "W"
    }
  }
]
```

### outputs.json

Snapshot of expected sensor outputs after optimization.
This file is generated and updated by the test runner.

## Time freezing

The test runner extracts the timestamp from `environment.json` and uses freezegun for deterministic results.
All datetime operations during the test see this frozen time.

## Running scenarios

Scenarios carry the `scenario` marker and are deselected from the default test run:

```bash
# Run all scenarios
uv run pytest -m scenario

# Run specific scenario
uv run pytest -m scenario -k scenario1

# Update snapshots
uv run pytest -m scenario --snapshot-update
```

### Build the frontend card first

Scenario tests render topology SVGs by shelling out to the card's scenario export script.
Without a build, **every scenario fails** with `Card export script not found`, which reads like an optimizer regression and is not one:

```bash
npm --prefix frontend/haeo-forecast-card ci
npm --prefix frontend/haeo-forecast-card run build
```

CI does this before its scenario job, and `uv run check` does it automatically.
Running scenarios by hand means doing it yourself once.

## Creating new scenarios

The usual path is a user's diagnostics download, which becomes a regression test directly:

1. Ask the user for Settings → Devices & Services → HAEO → Download Diagnostics
2. Create `tests/scenarios/<name>/` and save the download as `<name>/scenario.json`
3. Run the scenario suite once — the runner splits the unified file into the four files and deletes the original
4. Review the generated `outputs.json` and commit

Name the folder for the behavior under test rather than the next number in sequence, since discovery is a glob.

To hand-author a scenario instead:

1. Create new folder: `tests/scenarios/scenario_name/`
2. Add `config.json` with hub and element configuration
3. Add `environment.json` with freeze timestamp
4. Add `inputs.json` with sensor states to inject
5. Run tests - `outputs.json` will be generated
6. Review and commit the generated outputs

## Snapshot format

Each scenario has its own `outputs.json` file capturing the sensor states after optimization.
Snapshots include state values, attributes, forecasts, and metadata.

## Reading a scenario diff

A changed `outputs.json` means optimizer behavior changed.
Decide first whether that is intended — `--snapshot-update` is not a way to make a test pass.

- **Values shift slightly everywhere**: usually a solver tie-break or blend weight change.
    Confirm the objective value is unchanged before accepting.
- **One element's sensors change**: narrow to that adapter's `outputs()` or its model element.
- **Shadow prices change but power does not**: a constraint was added, removed, or reformulated.
    The primal solution is the same but the duals moved.
- **Optimization status becomes failed**: the model is infeasible.
    Look for a newly over-constraining constraint or a policy compilation change.

## Debugging scenarios

Visualizations are regenerated into `scenario*/visualizations/` on each run and are deterministic enough to commit.
Open them to see the network topology and the dispatch plan.

To optimize a scenario without Home Assistant in the loop:

```bash
uv run diag --file tests/scenarios/scenario1/            # rerun the optimization
uv run diag --file tests/scenarios/scenario1/ --compare  # stored vs recomputed, side by side
uv run diag --file tests/scenarios/scenario1/ -o         # stored outputs only
```

To browse the same data in a live Home Assistant instance, use `uv run sim scenario1`.
See [local simulation](../../../docs/developer-guide/local-sim.md).
