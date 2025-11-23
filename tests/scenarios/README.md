# HAEO Scenario Tests

Quick start guide for testing HAEO with real Home Assistant data.

## Quick Start

### From Diagnostics (Recommended)

Download diagnostics from Home Assistant UI and save directly as a scenario:

1. In Home Assistant: Settings → Devices & Services → HAEO → Download Diagnostics
2. Save the downloaded file as `tests/scenarios/my_scenario/scenario.json`

The diagnostics output is directly usable as a scenario test - no additional processing needed.

## Test Structure

Each scenario uses a single file:

```
scenario_name/
└── scenario.json   # Single file with config, environment, inputs, outputs
```

All scenarios are automatically discovered and tested by `tests/scenarios/test_scenarios.py`.
Snapshots are stored in `tests/scenarios/snapshots/test_scenarios.ambr`.

## What's in Diagnostics Format

The diagnostics output has a flat structure with four main keys (alphabetically sorted):

- **config**: HAEO configuration (participants, horizon_hours, period_minutes) - user editable
- **environment**: HA version, HAEO version, timestamp, timezone - user editable for testing
- **inputs**: All input sensor states with attributes and forecasts
- **outputs**: Output sensor states from optimization (compared against actual results in tests)

The environment.timestamp is used as the freeze time for the test, and outputs are compared with actual optimization results.

## Usage Examples

```bash
# From Home Assistant URL (interactive token prompt)
./tests/scenarios/filter_states.py http://ha.local:8123 -o scenario/states.json sensor.battery sensor.solar

# From file with patterns file
./tests/scenarios/filter_states.py states.json -o scenario/states.json --patterns-from-file sensors.txt

# Multiple patterns from file
./tests/scenarios/filter_states.py http://ha.local:8123 \
    -o scenario/states.json sensor.battery_soc sensor.import_price sensor.house_load
```

## Basic Configuration

```json
{
  "integration_type": "hub",
  "name": "Test Network",
  "participants": {
    "battery": {
      "element_type": "battery",
      "capacity": 10000,
      "initial_charge_percentage": "sensor.battery_soc",
      "max_power": 5000
    },
    "solar": {
      "element_type": "photovoltaics",
      "max_power": "sensor.solar_power"
    },
    "grid": {
      "element_type": "grid",
      "import_price": "sensor.electricity_price",
      "export_price": "sensor.feed_in_tariff"
    },
    "load": {
      "element_type": "constant_load",
      "power": "sensor.house_power"
    }
  },
  "connections": [
    [
      "solar",
      "battery"
    ],
    [
      "solar",
      "grid"
    ],
    [
      "battery",
      "grid"
    ],
    [
      "grid",
      "load"
    ],
    [
      "battery",
      "load"
    ]
  ]
}
```

## Running Tests

```bash
# Run all scenarios (use -m scenario to enable scenario tests)
uv run pytest tests/scenarios/test_scenarios.py -m scenario

# Run specific scenario by test ID
uv run pytest tests/scenarios/test_scenarios.py::test_scenarios[scenario1] -m scenario -v

# Update snapshots after changes
uv run pytest tests/scenarios/test_scenarios.py -m scenario --snapshot-update
```

## Common Issues

- **Token expired**: Generate new token in Home Assistant UI
- **Connection fails**: Check HA is running and URL is correct
- **States file too large**: Filter to only relevant sensors
- **Integration fails**: Verify all sensor names exist in states.json

## Key Sensor Patterns

- `sensor.battery_*` - Battery sensors
- `sensor.solar_*` - Solar generation
- `sensor.grid_*` - Grid power/pricing
- `sensor.price_*` - Energy pricing
- `input_number.*` - Configuration entities
