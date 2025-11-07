# Test Sensor Packages

This directory contains Home Assistant sensor configurations generated from `states.json` for testing the HAEO integration.

## Overview

43 sensors organized by Home Assistant integration domain, each using the command_line sensor integration with a Python transformation script:

- **JSON Files**: Store sensor state and attributes extracted from `states.json`
- **YAML Configurations**: Minimal configuration using `command_line` sensor integration
- **Transform Script**: `transform_sensor.py` applies transformations (date shifting, forecast reordering, or passthrough)
- **JSON Attributes**: All sensor metadata (friendly_name, unit_of_measurement, device_class, etc.) loaded from JSON attributes

## Architecture

### Command Line Sensor Pattern

Each sensor uses Home Assistant's `command_line` integration to execute a Python transformation script that outputs JSON:

```yaml
sensor_name:
  command_line:
    - sensor:
        unique_id: sensor.entity_id
        command: >
          python3 config/transform_sensor.py path/to/sensor.json transform_type [params]
        value_template: '{{ value_json.state }}'
        json_attributes_path: $.attributes
        json_attributes:
          - friendly_name
          - unit_of_measurement
          - device_class
          # ... additional attributes
        scan_interval: 3600
```

**Key Points**:

- YAML configuration is minimal - only non-derivable fields (unique_id, command, value_template, json_attributes list, scan_interval)
- All sensor metadata comes from JSON attributes (friendly_name, unit_of_measurement, device_class, state_class, icon)
- Transform script reads JSON file, applies transformation, outputs: `{"state": "value", "attributes": {...}}`
- Home Assistant merges JSON attributes into sensor entity

### Transform Script

`config/transform_sensor.py` supports three transform types:

1. **day_offset N**: Shifts all timestamps by N days (used for solar forecasts)

    ```bash
    python3 config/transform_sensor.py sensor.json day_offset 0  # today (no shift)
    python3 config/transform_sensor.py sensor.json day_offset 1  # tomorrow (+1 day)
    python3 config/transform_sensor.py sensor.json day_offset 7  # 7 days ahead
    ```

2. **wrap_forecasts**: Reorders forecast entries to start from current time-of-day, shifts dates forward

    ```bash
    python3 config/transform_sensor.py sensor.json wrap_forecasts
    ```

    - Finds forecast entry closest to current time-of-day
    - Reorders: entries from that point forward, then earlier entries
    - Shifts dates forward from today while preserving time-of-day
    - Creates rolling 24-hour window starting "now"

3. **passthrough**: Returns data unchanged (used for static sensors)

    ```bash
    python3 config/transform_sensor.py sensor.json passthrough
    ```

## Directory Structure

```
packages/
├── open_meteo_solar_forecast/  # 32 sensors (solar forecasts with day_offset transform)
│   ├── energy_production_today_east.json
│   ├── energy_production_today_east.yaml
│   └── ...
├── amberelectric/              # 4 sensors (forecasts with wrap_forecasts, prices with passthrough)
│   ├── home_general_forecast.json
│   ├── home_general_forecast.yaml
│   └── ...
└── sigen/                      # 7 sensors (static sensors with passthrough)
    ├── sigen_plant_pv_power.json
    ├── sigen_plant_pv_power.yaml
    └── ...
```

## Sensor Types

### Open Meteo Solar Forecast (32 sensors)

**Entity pattern**: `sensor.energy_production_{period}_{direction}`

- **Periods**: `today`, `tomorrow`, `d2`, `d3`, `d4`, `d5`, `d6`, `d7`
- **Directions**: `east`, `west`, `north`, `south`

**Transform type**: `day_offset N` where N varies by period:

- `today` → day_offset 0 (no shift)
- `tomorrow` → day_offset 1
- `d2` → day_offset 2, `d3` → day_offset 3, etc.

**Attributes**:

- `watts`: Dictionary of ISO 8601 timestamp→watt mappings (timestamps shifted by N days)
- `wh_period`: Dictionary of ISO 8601 timestamp→wh mappings (timestamps shifted by N days)
- `unit_of_measurement`: "kWh"
- `device_class`: "energy"
- `friendly_name`: Human-readable name (e.g., "Energy Production Today East")

### Amber Electric (4 sensors)

**Entities**:

- `sensor.home_feed_in_forecast` - Feed-in tariff forecast
- `sensor.home_feed_in_price` - Current feed-in tariff price
- `sensor.home_general_forecast` - General usage forecast
- `sensor.home_general_price` - Current general usage price

**Transform type**:

- **Forecast sensors** (`*_forecast`): `wrap_forecasts`
    - Reorders `forecasts` attribute to start from current time-of-day
    - Finds forecast entry closest to now (by time-of-day)
    - Reorders: entries from that point → end, then beginning → that point
    - Shifts dates forward from today while preserving time-of-day
    - Creates rolling 24-hour window starting "now"
- **Price sensors** (`*_price`): `passthrough`
    - No transformation, returns all attributes unchanged

**Attributes**:

- `forecasts`: List of forecast objects with `start_time`, `end_time`, `per_kwh`, `spot_per_kwh`, etc. (forecast sensors only)
- `channel_type`: "general" or "feedIn"
- `unit_of_measurement`: "\$/kWh"
- `attribution`: Amber Electric attribution text
- `friendly_name`: Human-readable name

### SiGen (7 sensors)

**Entities**:

- `sensor.sigen_plant_battery_state_of_charge` - Battery SOC (%)
- `sensor.sigen_plant_consumed_power` - Power consumption (W)
- `sensor.sigen_plant_ess_rated_charging_power` - Max charge rate (W)
- `sensor.sigen_plant_ess_rated_discharging_power` - Max discharge rate (W)
- `sensor.sigen_plant_max_active_power` - Max active power (W)
- `sensor.sigen_plant_pv_power` - Solar PV power (W)
- `sensor.sigen_plant_rated_energy_capacity` - Battery capacity (Wh)

**Transform type**: `passthrough` - static state sensors, no transformation needed

**Attributes**:

- `state_class`: "measurement"
- `unit_of_measurement`: "W", "%", or "Wh" depending on sensor
- `device_class`: "power", "battery", or "energy" depending on sensor
- `icon`: Material Design Icons identifier
- `friendly_name`: Human-readable name

## File Organization

Each sensor has two files:

- `{entity_name}.json` - Sensor state and attributes extracted from `states.json`
- `{entity_name}.yaml` - Minimal Home Assistant `command_line` sensor configuration

### JSON File Format

```json
{
  "entity_id": "sensor.entity_name",
  "state": "42.5",
  "attributes": {
    "friendly_name": "Sensor Display Name",
    "unit_of_measurement": "kWh",
    "device_class": "energy",
    "state_class": "measurement",
    "icon": "mdi:solar-power",
    "custom_attr": "value"
  }
}
```

### YAML File Format

```yaml
# Comment describing sensor
entity_name:
  command_line:
    - sensor:
        unique_id: sensor.entity_name
        command: |
          python3 config/transform_sensor.py \
           config/packages/domain/entity_name.json \
           transform_type \
           [params]
        value_template: '{{ value_json.state }}'
        json_attributes_path: $.attributes
        json_attributes:
          - friendly_name
          - unit_of_measurement
          - device_class
          - state_class
          - custom_attr
        scan_interval: 3600
```

**Important**: The `json_attributes` list must include all keys from the JSON file's `attributes` object that should be exposed as sensor attributes.

## Usage

To use these sensors in Home Assistant:

1. Copy the `packages/` directory to your Home Assistant config directory
2. Ensure packages are enabled in `configuration.yaml`:
    ```yaml
    homeassistant:
      packages: !include_dir_named packages
    ```
3. Restart Home Assistant

## Adding New Sensors

To add a new test sensor:

1. **Create JSON file** with sensor state and attributes:

    ```bash
    # Extract from states.json or create manually
    cat > config/packages/domain/new_sensor.json << 'EOF'
    {
      "entity_id": "sensor.new_sensor",
      "state": "123.45",
      "attributes": {
        "friendly_name": "New Sensor Name",
        "unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement"
      }
    }
    EOF
    ```

2. **Create YAML configuration**:

    ```yaml
    # config/packages/domain/new_sensor.yaml
    new_sensor:
      command_line:
        - sensor:
            unique_id: sensor.new_sensor
            command: |
              python3 config/transform_sensor.py \
              config/packages/domain/new_sensor.json \
              passthrough
            value_template: '{{ value_json.state }}'
            json_attributes_path: $.attributes
            json_attributes:
              - friendly_name
              - unit_of_measurement
              - device_class
              - state_class
            scan_interval: 3600
    ```

3. **Choose transform type**:

    - `passthrough` - No transformation (most common)
    - `day_offset N` - Shift timestamps by N days (for forecast data)
    - `wrap_forecasts` - Reorder forecasts starting from current time-of-day

4. **Update json_attributes list**: Must match all keys in JSON `attributes` object

## Generation

These files were generated using `fix_all_packages.py`:

- Reads JSON files from each domain directory
- Generates corresponding YAML configurations with appropriate transforms
- Solar sensors: Uses `day_offset` transform with period-based offsets
- Amber forecast sensors: Uses `wrap_forecasts` transform
- Amber price & SiGen sensors: Uses `passthrough` transform

JSON files were extracted from `states.json` using jq:

```bash
# Example: Extract solar forecast sensors
jq -c '.[] | select(.entity_id | startswith("sensor.energy_production_"))' states.json | \
    while read -r line; do
    entity_id=$(echo "$line" | jq -r '.entity_id')
    entity_name="${entity_id#sensor.}"
    echo "$line" | jq '.' > "config/packages/open_meteo_solar_forecast/${entity_name}.json"
done
```

## Testing

These sensors provide realistic test data for HAEO development:

- Solar forecasts update daily with shifted dates
- Price forecasts continuously reorder based on current time
- Battery/power sensors provide static baseline values

All timestamps remain relative to "now", ensuring tests work regardless of when they're run.
