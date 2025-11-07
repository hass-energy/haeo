# Forecasts and Sensors

This page explains how HAEO uses forecast data from Home Assistant sensors for optimization.

## Overview

HAEO relies on forecast data for:

- **Electricity prices** (import/export)
- **Solar generation** (photovoltaics)
- **Load consumption** (forecast loads)

All forecasts must be provided through Home Assistant sensor entities with properly formatted forecast attributes.

## Forecast Attribute Format

Forecast sensors must provide a `forecast` attribute with timestamped values:

```yaml
attributes:
  forecast:
    - datetime: '2025-10-11T12:00:00+00:00'
      value: 5.2
    - datetime: '2025-10-11T12:05:00+00:00'
      value: 5.1
    - datetime: '2025-10-11T12:10:00'
      value: 4.9
    # ... more timestamped values
```

### Requirements

- **`datetime`**: ISO 8601 format with timezone
- **`value`**: Numeric value (power in kW, price in \$/kWh, etc.)

### Format Detection

HAEO uses heuristics to automatically detect the forecast format and time alignment.
It handles various forecast styles from different integrations without requiring manual configuration.
The optimizer intelligently interprets timestamps to align forecast data with optimization periods.

!!! info "Partial Coverage"

    If forecast data doesn't cover the entire optimization horizon, HAEO uses **zero values** for periods without data.
    For best results, ensure forecasts cover your full horizon (e.g., 48 hours of data for a 48-hour horizon).

## Using Multiple Forecast Sensors

When you configure multiple forecast sensors for a single element (e.g., separate today and tomorrow price sensors), HAEO automatically merges them into a continuous timeline.

!!! tip "Multiple Forecast Sources"

    For price forecasts split across time periods:

    ```yaml
    Import Price:
      - sensor.price_today     # Covers today
      - sensor.price_tomorrow  # Covers tomorrow
    ```

    HAEO combines these into a seamless forecast covering both periods.

## Supported Forecast Integrations

HAEO works with any integration that provides forecast attributes in the standard format. Common integrations include:

### Solar Forecasts

- **[Open-Meteo Solar Forecast](https://github.com/rany2/ha-open-meteo-solar-forecast)** - Free, accurate 7-day forecasts
- **[Solcast Solar](https://github.com/BJReplay/ha-solcast-solar)** - Professional solar forecasting service

### Electricity Prices

- **[Amber Electric](https://www.home-assistant.io/integrations/amberelectric/)** - Australian real-time wholesale pricing with 24-hour forecasts

### Custom Forecasts

You can create custom forecast sensors using Home Assistant templates (see examples below).

## Creating Forecast Sensors with Templates

### Time-of-Use Tariff

For fixed pricing schedules with varying time periods:

```yaml
template:
  - sensor:
      - name: Time of Use Import Price
        unique_id: tou_import_price
        unit_of_measurement: $/kWh
        state: >
          {% set now_time = now() %}
          {% set hour = now_time.hour %}
          {% set minute = now_time.minute %}

          {# Peak: 4pm-9pm weekdays #}
          {% if now_time.weekday() < 5 and hour >= 16 and hour < 21 %}
            0.52
          {# Off-peak: 10pm-7am all days #}
          {% elif hour >= 22 or hour < 7 %}
            0.18
          {# Shoulder: all other times #}
          {% else %}
            0.28
          {% endif %}
        attributes:
          forecast: >
            {% set forecast_list = [] %}
            {% set start = now().replace(minute=0, second=0, microsecond=0) %}

            {# Define price periods (start, end, is_weekday_only, price) #}
            {% set periods = [
              (22, 24, false, 0.18),  {# Off-peak night #}
              (0, 7, false, 0.18),     {# Off-peak morning #}
              (7, 16, false, 0.28),    {# Shoulder morning/afternoon #}
              (16, 21, true, 0.52),    {# Peak weekday evening #}
              (16, 21, false, 0.28),   {# Shoulder weekend evening #}
              (21, 22, false, 0.28)    {# Shoulder late evening #}
            ] %}

            {# Generate 48 hours of forecast #}
            {% for hour_offset in range(48) %}
              {% set forecast_time = start + timedelta(hours=hour_offset) %}
              {% set h = forecast_time.hour %}
              {% set is_weekday = forecast_time.weekday() < 5 %}

              {# Determine price for this hour #}
              {% set price = 0.28 %}  {# Default shoulder #}
              {% if h >= 22 or h < 7 %}
                {% set price = 0.18 %}  {# Off-peak #}
              {% elif is_weekday and h >= 16 and h < 21 %}
                {% set price = 0.52 %}  {# Peak #}
              {% endif %}

              {# Add entry #}
              {% set entry = {
                "datetime": forecast_time.isoformat(),
                "value": price
              } %}
              {% set _ = forecast_list.append(entry) %}
            {% endfor %}

            {{ forecast_list }}
```

This example shows a realistic tariff structure with different rates for weekdays vs weekends and non-uniform time periods.

### Fixed Price Forecast {#constant-price-as-forecast}

For a constant price that doesn't vary over time:

```yaml
template:
  - sensor:
      - name: Fixed Export Price
        unique_id: fixed_export_price
        unit_of_measurement: $/kWh
        state: '0.08'
        attributes:
          forecast: >
            {% set start = now() %}
            {% set end = start + timedelta(hours=48) %}
            [
              {"datetime": "{{ start.isoformat() }}", "value": 0.08},
              {"datetime": "{{ end.isoformat() }}", "value": 0.08}
            ]
```

Only start and end timestamps are needed for constant values.
HAEO will fill in the intermediate periods automatically.

### Historic Load Forecast

Use past consumption data to forecast future load based on same-day-last-week statistics:

```yaml
template:
  - sensor:
      - name: House Load Forecast
        unique_id: house_load_forecast
        unit_of_measurement: kW
        device_class: power
        state: "{{ states('sensor.home_power_consumption') | float(0) }}"
        attributes:
          forecast: >
            {% set forecast_list = [] %}
            {% set start = now() %}

            {# Generate forecast for next 48 hours using weekly pattern #}
            {% for hour in range(48) %}
              {% set forecast_time = start + timedelta(hours=hour) %}

              {# Look back exactly 7 days to get same time last week #}
              {% set history_time = forecast_time - timedelta(days=7) %}

              {# Get average consumption from that hour last week #}
              {# Using 1-hour window centered on the target time #}
              {% set history_start = history_time - timedelta(minutes=30) %}
              {% set history_end = history_time + timedelta(minutes=30) %}

              {%
                set avg_power = state_attr('sensor.home_power_consumption', 'statistics')
              %}
              {% if avg_power %}
                {% set power_value = avg_power.mean | float(1.0) %}
              {% else %}
                {# Fallback: query last week's value directly #}
                {%
                  set power_value =
                    states.sensor.home_power_consumption.history(history_start, history_end)
                                      | map(attribute='state')
                                      | map('float', 0)
                                      | list
                                      | average
                                      | default(1.0)
                %}
              {% endif %}

              {% set entry = {
                "datetime": forecast_time.isoformat(),
                "value": power_value
              } %}
              {% set _ = forecast_list.append(entry) %}
            {% endfor %}

            {{ forecast_list }}
```

This approach uses historical statistics to create realistic load forecasts based on your actual usage patterns.

!!! note "Long-term Statistics Required"

    For history-based forecasts to work properly, ensure your consumption sensor has recorder enabled and sufficient historical data (at least one week).

## Troubleshooting Forecasts

### Insufficient Forecast Coverage

**Problem**: Optimization uses zero values for parts of the horizon.

**Solution**: Ensure forecasts cover your entire horizon.
For example, a 48-hour optimization horizon needs 48 hours of forecast data.

**Check your sources**:

- Template sensors: Ensure your loop generates enough hours
- Integration sensors: Verify the integration provides sufficient forecast length
- Multiple sensors: Confirm combined coverage spans the full horizon

### Forecast Not Updating

**Check**:

1. Sensor state updates regularly
2. `forecast` attribute exists and has data
3. Datetime format is correct (ISO 8601 with timezone)
4. Values are numeric, not strings

### Incorrect Values

**Common issues**:

- Wrong units (W instead of kW, cents instead of dollars)
- Missing timezone in datetime
- String values instead of numbers

## Best Practices

### Update Frequency

Forecast sensors should update regularly, but not excessively:

- **Prices**: When new forecast data becomes available (typically once or twice daily)
- **Solar**: Every 1-4 hours or when weather forecasts update
- **Load**: Every 1-6 hours, or when your usage pattern model updates

!!! tip "Avoid Over-Updating"

    HAEO re-optimizes when forecast data changes.
    Updating forecasts every few minutes provides no benefit and wastes computational resources.
    Match update frequency to how often forecast data actually changes meaningfully.

### Forecast Resolution

Finer time resolution improves optimization:

- **Good**: Hourly data points
- **Better**: 30-minute data points
- **Best**: 5-15 minute data points

Match or exceed your HAEO period setting (e.g., 5-minute periods need ≤5-minute forecast resolution).

### Data Quality

Ensure forecasts are realistic:

- Solar can't exceed panel capacity
- Loads should reflect actual usage patterns
- Prices should be in correct units

Poor forecasts lead to suboptimal scheduling.

## Related Documentation

- [Grid Configuration](elements/grid.md) - Using price forecasts
- [Photovoltaics Configuration](elements/photovoltaics.md) - Using solar forecasts
- [Load Configuration](elements/constant-load.md) - Using load forecasts
- [Troubleshooting](troubleshooting.md#forecasts-are-not-long-enough) - Forecast issues

[:material-arrow-right: Continue to Element Configuration](elements/index.md)
