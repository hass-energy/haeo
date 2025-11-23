# HAEO Scenario Tests

Quick start guide for testing HAEO with real Home Assistant data.

## Quick Start

### Option 1: From Diagnostics (Easiest - Recommended)

Download diagnostics from Home Assistant UI and extract scenario data:

```python
import json

with open('diagnostics.json') as f:
    diagnostics = json.load(f)

scenario_format = diagnostics['scenario_format']

# Save config
with open('tests/scenarios/my_scenario/config.json', 'w') as f:
    json.dump(scenario_format['config'], f, indent=2)

# Save states  
with open('tests/scenarios/my_scenario/states.json', 'w') as f:
    json.dump(scenario_format['states'], f, indent=2)
```

### Option 2: Direct from Home Assistant

```bash
# Fetches states and filters in one command (prompts for token)
./tests/scenarios/filter_states.py http://homeassistant.local:8123 \
    --output tests/scenarios/my_scenario/states.json \
    sensor.battery sensor.solar sensor.grid
```

### Option 3: From existing file

```bash
# Filter existing states.json file
./tests/scenarios/filter_states.py path/to/states.json \
    --output tests/scenarios/my_scenario/states.json \
    sensor.battery sensor.solar sensor.grid
```

## Test Structure

Each scenario needs:

```
scenario_name/
├── states.json     # Filtered HA states (from diagnostics or filter_states.py)
└── config.json     # HAEO configuration (from diagnostics or manual)
```

All scenarios are automatically discovered and tested by `tests/scenarios/test_scenarios.py`.
Snapshots are stored in `tests/scenarios/snapshots/test_scenarios.ambr`.

## What's in Diagnostics Scenario Format

The diagnostics `scenario_format` section includes:

- **config**: Complete participant configurations, horizon_hours, period_minutes
- **states**: All input sensor states with attributes and forecasts
- **output_states** (optional): Output sensor states if optimization has run (useful for diagnostics)

This makes it easy to capture a problematic state and create a reproducible test scenario for debugging.

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
