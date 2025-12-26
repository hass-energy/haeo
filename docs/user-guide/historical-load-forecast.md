# Historical Load Forecast

HAEO doesn't generate load forecasts itself, but you can create forecasts based on historical consumption data.
This approach works well for loads that follow predictable daily patterns.

## Recommended: Use HAFO

The easiest way to create historical load forecasts is with [HAFO (Home Assistant Forecaster)](https://hafo.haeo.io).
HAFO is a companion integration designed specifically for this purpose:

1. Install HAFO via HACS
2. Create a forecast helper for your load sensor
3. Configure HAEO to use the HAFO sensor as its load forecast source

HAFO handles all the complexity automatically - fetching historical statistics, shifting them forward, and cycling patterns to fill any forecast horizon.
See the [HAFO documentation](https://hafo.haeo.io) for installation and configuration details.

## Manual Approach

If you prefer not to install another integration, you can create forecasts manually using Home Assistant's python_script integration.
The strategy is straightforward: fetch the same hour from 7 days ago, then use that pattern for the next 7 days.

### Prerequisites

Enable the [Python Scripts integration](https://www.home-assistant.io/integrations/python_script/) in Home Assistant.
Add the following to your `configuration.yaml`:

```yaml
python_script:
```

Create the `python_scripts` directory in your config folder if it doesn't exist.

### Step 1: Create the Forecast Sensor Script

Create `config/python_scripts/set_forecast_sensor.py`:

```python
entity_id = data.get("entity_id")
source_entity = data.get("source_entity")
forecast = data.get("forecast")
current_value = data.get("current_value")

if not entity_id:
    logger.error("No entity_id provided")
elif not source_entity:
    logger.error("No source_entity provided")
elif forecast is None:
    logger.error("No forecast data provided")
else:
    source = hass.states.get(source_entity)
    if source is None:
        logger.error("Source entity %s not found", source_entity)
    else:
        source_name = source.attributes.get("friendly_name", source_entity)
        hass.states.set(
            entity_id,
            current_value,
            {
                "forecast": forecast,
                "unit_of_measurement": source.attributes.get("unit_of_measurement"),
                "device_class": source.attributes.get("device_class"),
                "state_class": source.attributes.get("state_class"),
                "icon": source.attributes.get("icon", "mdi:flash"),
                "friendly_name": f"{source_name} Forecast",
            },
        )
```

This script creates a sensor with a `forecast` attribute that HAEO can read.
It copies `unit_of_measurement`, `device_class`, `state_class`, and `icon` from the source sensor, and appends "Forecast" to the friendly name.

### Step 2: Create the Extraction Script

Create a Home Assistant script that fetches historical data and publishes the forecast.
Go to **Settings** → **Automations & Scenes** → **Scripts** → **Add Script** and use YAML mode:

```yaml
alias: Extract Load Forecast
description: Fetches load history from 7 days ago and publishes forecast
mode: single
sequence:
  - variables:
      consumed_power_sensor: sensor.your_load_power_sensor
      forecast_sensor_entity: sensor.load_power_forecast
      num_prediction_days: 7
  - action: recorder.get_statistics
    data:
      start_time: '{{ (now().replace(minute=0, second=0, microsecond=0) - timedelta(days=num_prediction_days)).isoformat()
        }}'
      end_time: '{{ now().replace(minute=0, second=0, microsecond=0).isoformat() }}'
      statistic_ids: '{{ consumed_power_sensor }}'
      period: hour
      types: mean
    response_variable: history
    alias: Fetch Load History
  - variables:
      start_of_hour: '{{ now().replace(minute=0, second=0, microsecond=0) }}'
      load_forecast_json: |-
        {% set ns = namespace(
          input=history.statistics[consumed_power_sensor],
          output=[]
        ) %}
        {% for load in ns.input %}
          {% set load_start = load.start | as_datetime | as_local + timedelta(days=num_prediction_days) %}
          {% set load_value = load.mean | float(0) | round(3) %}
          {% set ns.output = ns.output + [{"time": load_start.isoformat(), "value": load_value}] %}
        {% endfor %}
        {{ ns.output }}
      current_value: |-
        {% set start_of_hour = now().replace(minute=0, second=0, microsecond=0) %}
        {% set ns = namespace(
          input=history.statistics[consumed_power_sensor],
          result=states(consumed_power_sensor) | float(0) | round(3)
        ) %}
        {% for load in ns.input %}
          {% set load_start = load.start | as_datetime | as_local + timedelta(days=num_prediction_days) %}
          {% if load_start == start_of_hour %}
            {% set ns.result = load.mean | float(0) | round(3) %}
          {% endif %}
        {% endfor %}
        {{ ns.result }}
  - data:
      entity_id: '{{ forecast_sensor_entity }}'
      source_entity: '{{ consumed_power_sensor }}'
      forecast: '{{ load_forecast_json }}'
      current_value: '{{ current_value }}'
    alias: Publish Load Forecast Sensor
    action: python_script.set_forecast_sensor
```

**Customize these variables**:

| Variable                 | Description                                 | Example                       |
| ------------------------ | ------------------------------------------- | ----------------------------- |
| `consumed_power_sensor`  | Your existing power consumption sensor      | `sensor.house_consumed_power` |
| `forecast_sensor_entity` | Entity ID for the new forecast sensor       | `sensor.load_power_forecast`  |
| `num_prediction_days`    | How many days of history to fetch and shift | `7`                           |

The script fetches the last 7 days of hourly mean values and shifts them forward by 7 days.
Units are copied from the source sensor automatically.

### Step 3: Create Hourly Automation

Create an automation to run the extraction script every hour.
Go to **Settings** → **Automations & Scenes** → **Create Automation**:

```yaml
alias: Update Load Forecast Hourly
trigger:
  - platform: time_pattern
    minutes: 0
  - platform: homeassistant
    event: start
action:
  - action: script.extract_load_forecast
```

This runs at the top of every hour and on Home Assistant startup, since python_script sensors don't persist across restarts.

### Using with HAEO

Configure your Load element to use the forecast sensor:

| Field        | Value                      |
| ------------ | -------------------------- |
| **Name**     | House Load                 |
| **Forecast** | sensor.load_power_forecast |

HAEO reads the `forecast` attribute and uses the historical pattern for optimization.

### Forecast Format

The forecast attribute should be an array of time-value pairs:

```json
[
  {
    "time": "2025-11-30T00:00:00+10:00",
    "value": 1.234
  },
  {
    "time": "2025-11-30T01:00:00+10:00",
    "value": 1.456
  },
  {
    "time": "2025-11-30T02:00:00+10:00",
    "value": 1.789
  }
]
```

Each entry contains:

- `time`: ISO 8601 timestamp string with timezone (e.g., `2025-11-30T00:00:00+10:00`)
- `value`: Numeric forecast value in the sensor's unit of measurement

!!! tip "Initial Setup"

    Run the script manually once after creating it to populate the forecast sensor immediately.
    Go to **Developer Tools** → **Services**, select `script.extract_load_forecast`, and click **Call Service**.
