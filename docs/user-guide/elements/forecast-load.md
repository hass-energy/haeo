# Forecast Load

Forecast loads represent time-varying power consumption based on forecast data.
Use this for variable household consumption, scheduled devices, or HVAC systems.

## Configuration Fields

| Field        | Type            | Required | Default | Description                          |
| ------------ | --------------- | -------- | ------- | ------------------------------------ |
| **Name**     | String          | Yes      | -       | Unique identifier                    |
| **Type**     | "Forecast Load" | Yes      | -       | Element type                         |
| **Forecast** | Sensor(s)       | Yes      | -       | Power consumption forecast sensor(s) |

## Name

Use descriptive names that indicate what the load represents:

- ✅ "House Load", "Variable Consumption", "HVAC Load", "EV Charger"
- ❌ "Load1", "Forecast", "Thing"

## Forecast

One or more Home Assistant sensor entities providing consumption forecasts in kilowatts (kW).

### Single Forecast Sensor

```yaml
Forecast: sensor.house_load_forecast
```

### Multiple Forecast Sensors

HAEO will merge multiple sensors into a continuous timeline:

```yaml
Forecast:
  - sensor.load_forecast_today
  - sensor.load_forecast_tomorrow
```

### Forecast Format

Forecast sensors must provide timestamped future values in attributes:

```yaml
attributes:
  forecast:
    - datetime: "2025-10-13T12:00:00+00:00"
      value: 2.5  # kW
    - datetime: "2025-10-13T12:05:00+00:00"
      value: 2.3
    # ... more timestamped values
```

See the [Forecasts & Sensors guide](../forecasts-and-sensors.md) for detailed format requirements and examples.

## Creating Load Forecasts

### History-Based Forecast

Use past consumption to predict future load:

```yaml
template:
  - sensor:
      - name: "House Load Forecast"
        unique_id: house_load_forecast
        unit_of_measurement: "kW"
        device_class: power
        state: "{{ states('sensor.home_power_consumption') | float(0) }}"
        attributes:
          forecast: >
            {% set forecast_list = [] %}
            {% set start = now() %}

            {% for hour in range(48) %}
              {% set forecast_time = start + timedelta(hours=hour) %}
              {% set history_time = forecast_time - timedelta(days=7) %}

              {% set avg_power = states.sensor.home_power_consumption
                                  .history(history_time - timedelta(minutes=30),
                                          history_time + timedelta(minutes=30))
                                  | map(attribute='state')
                                  | map('float', 0)
                                  | list
                                  | average
                                  | default(1.0) %}

              {% set entry = {
                "datetime": forecast_time.isoformat(),
                "value": avg_power
              } %}
              {% set _ = forecast_list.append(entry) %}
            {% endfor %}

            {{ forecast_list }}
```

This uses same-day-last-week data to create realistic forecasts.

### Pattern-Based Forecast

Use typical hourly patterns:

```yaml
template:
  - sensor:
      - name: "Typical House Load"
        unique_id: typical_house_load
        unit_of_measurement: "kW"
        state: >
          {% set hour = now().hour %}
          {% set patterns = {
            0: 0.8, 1: 0.7, 2: 0.7, 3: 0.7, 4: 0.8, 5: 1.2,
            6: 2.5, 7: 3.0, 8: 2.0, 9: 1.5, 10: 1.2, 11: 1.5,
            12: 2.0, 13: 1.8, 14: 1.5, 15: 1.8, 16: 2.5, 17: 3.5,
            18: 4.0, 19: 3.5, 20: 3.0, 21: 2.5, 22: 2.0, 23: 1.5
          } %}
          {{ patterns[hour] }}
        attributes:
          forecast: >
            {% set patterns = {
              0: 0.8, 1: 0.7, 2: 0.7, 3: 0.7, 4: 0.8, 5: 1.2,
              6: 2.5, 7: 3.0, 8: 2.0, 9: 1.5, 10: 1.2, 11: 1.5,
              12: 2.0, 13: 1.8, 14: 1.5, 15: 1.8, 16: 2.5, 17: 3.5,
              18: 4.0, 19: 3.5, 20: 3.0, 21: 2.5, 22: 2.0, 23: 1.5
            } %}
            {% set forecast_list = [] %}
            {% set start = now().replace(minute=0, second=0, microsecond=0) %}

            {% for hour in range(48) %}
              {% set forecast_time = start + timedelta(hours=hour) %}
              {% set hour_of_day = forecast_time.hour %}
              {% set entry = {
                "datetime": forecast_time.isoformat(),
                "value": patterns[hour_of_day]
              } %}
              {% set _ = forecast_list.append(entry) %}
            {% endfor %}

            {{ forecast_list }}
```

### Scheduled Device Forecast

For predictable loads like EV charging:

```yaml
template:
  - sensor:
      - name: "EV Charging Schedule"
        unique_id: ev_charging_schedule
        unit_of_measurement: "kW"
        state: >
          {% set hour = now().hour %}
          {{ 7.4 if hour >= 22 or hour < 6 else 0 }}
        attributes:
          forecast: >
            {% set forecast_list = [] %}
            {% set start = now() %}

            {% for hour in range(48) %}
              {% set forecast_time = start + timedelta(hours=hour) %}
              {% set h = forecast_time.hour %}
              {% set power = 7.4 if h >= 22 or h < 6 else 0 %}

              {% set entry = {
                "datetime": forecast_time.isoformat(),
                "value": power
              } %}
              {% set _ = forecast_list.append(entry) %}
            {% endfor %}

            {{ forecast_list }}
```

## Configuration Example

```yaml
Name: House Load
Type: Forecast Load
Forecast: sensor.house_load_forecast
```

## Combined with Constant Load

For best results, separate baseline and variable consumption:

```yaml
# Constant baseline
Name: Base Load
Type: Constant Load
Power: 1.0  # kW

# Variable portion
Name: Variable Load
Type: Forecast Load
Forecast: sensor.variable_consumption
```

This approach:

- Makes forecasting easier (only forecast the variable portion)
- Ensures baseline is always covered
- Provides more accurate optimization

## Sensors Created

### Power Sensor

**Entity ID**: `sensor.{name}_power`

**Unit**: kW

**Description**: Current optimal power consumption based on forecast

The power sensor shows forecasted consumption values at each timestep, with forecast attributes containing future values.

## Troubleshooting

### Forecast Too Short

**Problem**: Optimization fails due to insufficient forecast data

**Solution**: Ensure forecast covers your entire horizon (e.g., 48 hours of data for 48-hour horizon)

Check your forecast sensor in Developer Tools → States to verify coverage.

### Inaccurate Forecasts

**Problem**: Optimization produces unrealistic schedules

**Solutions**:

1. **Verify units**: Ensure forecast is in kW (not W or kWh)
2. **Check data quality**: Review forecast values for reasonableness
3. **Tune forecast model**: Improve historical averaging or patterns
4. **Validate sensor**: Confirm forecast attribute format is correct

### Load Forecast Not Updating

**Problem**: Optimization uses stale forecast data

**Solutions**:

1. **Check sensor state**: Verify sensor updates regularly
2. **Review automation**: Ensure forecast sensor update trigger works
3. **Check time_period**: For statistics-based forecasts, confirm sufficient history exists

### Optimization Infeasible with Forecast

**Problem**: Solver can't find solution

**Solutions**:

1. **Check peak loads**: Forecast peaks may exceed supply capacity
2. **Review grid limits**: Ensure grid can import enough during high loads
3. **Verify connections**: Load must be connected to power sources
4. **Check forecast values**: Ensure no unrealistically high values

## When to Use Forecast Load

Use forecast loads for:

- ✅ Variable household consumption
- ✅ HVAC systems with weather-dependent usage
- ✅ Scheduled devices (EV charging, heat pumps)
- ✅ Time-of-day varying loads
- ✅ Commercial operations with predictable patterns

Avoid for:

- ❌ Pure baseline (use constant load)
- ❌ When forecast data is unavailable
- ❌ Initial testing (start with constant load)

## Multiple Forecast Loads

Configure separate forecast loads for different sources:

```yaml
# Household consumption
Name: House Load
Type: Forecast Load
Forecast: sensor.house_forecast

# EV charging
Name: EV Charger
Type: Forecast Load
Forecast: sensor.ev_schedule

# HVAC
Name: HVAC System
Type: Forecast Load
Forecast: sensor.hvac_forecast
```

Total load at each timestep = sum of all load elements.

## Related Documentation

- [Constant Load Configuration](constant-load.md) - For fixed consumption
- [Forecasts & Sensors Guide](../forecasts-and-sensors.md) - Creating forecast sensors
- [Load Modeling](../../modeling/loads.md) - Mathematical model
- [Connections](connections.md) - Connecting loads to the network

[:material-arrow-right: Continue to Node Configuration](node.md)
