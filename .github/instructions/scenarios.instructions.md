---
applyTo: tests/scenarios/**
description: Scenario testing standards
globs: [tests/scenarios/**]
alwaysApply: false
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

Mirrors the post-v1.3 `entry.as_dict()` shape (HA bookkeeping fields blocklisted):

```json
{
  "version": 1,
  "minor_version": 3,
  "domain": "haeo",
  "title": "Test Hub",
  "data": {
    "integration_type": "hub",
    "common": {
      "name": "Test Hub",
      "horizon_preset": "custom"
    },
    "tiers": {
      "tier_1_count": 12,
      "tier_1_duration": 5,
      "tier_2_count": 0,
      "tier_2_duration": 5,
      "tier_3_count": 0,
      "tier_3_duration": 30,
      "tier_4_count": 0,
      "tier_4_duration": 60
    },
    "advanced": {
      "debounce_seconds": 2,
      "advanced_mode": false
    }
  },
  "options": {},
  "subentries": [
    {
      "subentry_type": "battery",
      "title": "Battery",
      "data": {
        "element_type": "battery",
        "name": "Battery"
      }
    }
  ]
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

Scenarios are skipped in CI and require explicit invocation:

```bash
# Run all scenarios
uv run pytest tests/scenarios/ -m scenario

# Run specific scenario
uv run pytest tests/scenarios/ -m scenario -k scenario1

# Update snapshots
uv run pytest tests/scenarios/ -m scenario --snapshot-update
```

## Creating new scenarios

1. Create new folder: `tests/scenarios/scenario_name/`
2. Add `config.json` with hub and element configuration
3. Add `environment.json` with freeze timestamp
4. Add `inputs.json` with sensor states to inject
5. Run tests - `outputs.json` will be generated
6. Review and commit the generated outputs

## Snapshot format

Each scenario has its own `outputs.json` file capturing the sensor states after optimization.
Snapshots include state values, attributes, forecasts, and metadata.

## Debugging scenarios

Use `visualization.py` to generate charts of optimization results.
Visualizations are saved to `scenario*/visualizations/` for each run.
