---
name: scenarios
description: End-to-end scenario tests in tests/scenarios/ — creating a scenario from a user's diagnostics download, running them, updating outputs.json snapshots, and reading a scenario diff. Use when a scenario test fails, when reproducing a user-reported optimization result, or when adding a regression scenario.
---

# Scenario testing

Scenario tests are end-to-end integration tests with realistic configurations and time-frozen states.

## Structure

```
tests/scenarios/
├── test_scenarios.py         # Parametrized runner, one test per scenario folder
├── conftest.py               # Fixtures, including the scenario.json splitter
├── syrupy_json_extension.py  # Reads and writes outputs.json as the snapshot
├── visualization.py          # Topology and dispatch plan SVGs
└── scenario*/
    ├── config.json           # Hub and element configuration
    ├── environment.json      # Captured timestamps; optimization_start_time freezes time
    ├── inputs.json           # HA sensor states to inject
    └── outputs.json          # Expected sensor outputs (snapshot)
```

## Discovery

`_discover_scenarios()` in `test_scenarios.py` globs `scenario*/` and keeps only folders that hold all four JSON files.
No registration is needed, but a folder whose name does not start with `scenario`, or that lacks `outputs.json`, is silently skipped.

## Scenario files

### config.json

The hub config entry's data with its element subentries under `participants`, keyed by element name, plus the entry's `version` and `minor_version`.
The test sets the entry up at that version, so Home Assistant migrates an older config to the current schema exactly as it would a user's.
A config without `minor_version` is taken as current and is not migrated.

A config in the current schema looks like this, with each element's fields in the same sections as its stored subentry:

```json
{
  "version": 1,
  "minor_version": 4,
  "common": {
    "name": "Test Hub",
    "horizon": {
      "type": "preset",
      "value": "3_days"
    }
  },
  "advanced": {},
  "participants": {
    "Battery": {
      "name": "Battery",
      "element_type": "battery",
      "connection": {
        "type": "connection_target",
        "value": "Inverter"
      },
      "storage": {
        "capacity": {
          "type": "entity",
          "value": [
            "sensor.battery_capacity"
          ]
        }
      }
    }
  }
}
```

Copy an existing scenario's `config.json` rather than writing one from scratch, and keep the `version` and `minor_version` it carries.
A config from an older export, such as one with `common.horizon_preset`, must keep its older `minor_version` so it migrates.

### environment.json

Captured runtime context. The `optimization_start_time` is used as the test's freeze timestamp, and the `timezone` and `currency` are applied to Home Assistant.
Diagnostics from before HAEO recorded the currency have none, so add the user's currency when creating a scenario from one:

```json
{
  "ha_version": "2024.1.0",
  "haeo_version": "0.1.0",
  "timezone": "UTC",
  "currency": "AUD",
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

Scenarios carry the `scenario` marker.
The `test` gate excludes them and the `scenario` gate runs them, both in CI and in `uv run check`:

```bash
# Run all scenarios
uv run check scenario
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

CI does this before its scenario job, and the `scenario` gate of `uv run check` does it automatically.
Running scenarios by hand means doing it yourself once.

## Creating new scenarios

The usual path is a user's diagnostics download, which becomes a regression test directly:

1. Ask the user for Settings → Devices & Services → HAEO → Download Diagnostics
2. Create `tests/scenarios/scenario_<name>/` and save the download as `scenario_<name>/scenario.json`
3. Run the scenario suite once — a session fixture splits the unified file into the four files, taking `outputs.json` from the outputs the diagnostics recorded, and deletes the original
4. Run it again: the split happens after collection, so the new scenario is only picked up on the second run, which compares HAEO's results with the recorded outputs
5. If the results should replace the recorded outputs, rerun with `--snapshot-update`; review `outputs.json`, run `uv run check --fix` so prettier formats the split files, and commit

Name the folder `scenario_<behavior>` for the behavior under test rather than the next number in sequence.
The `scenario` prefix is required for discovery.

To hand-author a scenario instead:

1. Create `tests/scenarios/scenario_<name>/`
2. Add `config.json`, `environment.json`, and `inputs.json`
3. Add an `outputs.json` containing `{}` so discovery picks the folder up
4. Run `uv run pytest -m scenario -k scenario_<name> --snapshot-update` to fill `outputs.json`
5. Review and commit the generated outputs

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

Visualizations are regenerated into `scenario*/visualizations/` on each run and are committed.
Open them to see the network topology and the dispatch plan.

To optimize a scenario without Home Assistant in the loop:

```bash
uv run diag --file tests/scenarios/scenario1/            # rerun the optimization
uv run diag --file tests/scenarios/scenario1/ --compare  # stored vs recomputed, side by side
uv run diag --file tests/scenarios/scenario1/ -o         # stored outputs only
```

To browse the same data in a live Home Assistant instance, use `uv run sim scenario1`.
See [local simulation](../../../docs/developer-guide/local-sim.md).
