---
description: Scenario testing patterns
globs: [tests/scenarios/**]
alwaysApply: false
---

# Scenario testing

Scenario tests are end-to-end integration tests with realistic configurations and time-frozen states.

## Structure

```
tests/scenarios/
├── test_scenarios.py      # Centralized parameterized test runner
├── conftest.py            # Shared fixtures
├── snapshots/
│   └── test_scenarios.ambr
└── scenario*/
    ├── config.json        # Integration configuration
    └── states.json        # HA state data (includes timestamp)
```

## Auto-discovery

Test runner automatically discovers all `scenario*/` folders using `Path.glob("scenario*/")`.
No registration needed - just create a new folder.

## Scenario files

### config.json

Integration configuration matching the config flow schema:

```json
{
  "elements": {
    "battery": {
      "name": "Home Battery",
      "capacity": 10000,
      "power_limit": 5000
    }
  },
  "connections": []
}
```

### states.json

Home Assistant state data with required `now` timestamp:

```json
{
  "now": "2024-01-15T12:00:00+00:00",
  "states": {
    "sensor.solar_power": {
      "state": "3500",
      "attributes": {
        "unit_of_measurement": "W"
      }
    }
  }
}
```

## Time freezing

The test runner extracts the `now` timestamp from `states.json` and uses freezegun for deterministic results.
All datetime operations during the test see this frozen time.

## Running scenarios

- Scenarios require the `-m scenario` pytest marker
- Use `-k scenario_name` to run specific scenarios
- Use `--snapshot-update` to regenerate snapshots

## Creating new scenarios

1. Create new folder: `tests/scenarios/scenario_name/`
2. Add `config.json` with integration configuration
3. Add `states.json` with HA state data (must include `now` timestamp)
4. Run tests - auto-discovered automatically
5. Review and commit generated snapshots

## Snapshot format

All scenarios share a single snapshot file using syrupy JSON extension.
Snapshots capture:

- Optimization results
- Sensor states
- Element configurations

## Debugging scenarios

Use the visualization tools in `tests/scenarios/visualization.py` to generate charts of optimization results for debugging.
