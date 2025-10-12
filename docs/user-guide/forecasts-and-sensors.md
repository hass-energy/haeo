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
    - datetime: "2025-10-11T12:00:00+00:00"
      value: 5.2
    - datetime: "2025-10-11T12:05:00+00:00"
      value: 5.1
    - datetime: "2025-10-11T12:10:00"
      value: 4.9
    # ... more timestamped values
```

### Requirements

- **`datetime`**: ISO 8601 format with timezone
- **`value`**: Numeric value (power in kW, price in \$/kWh, etc.)
- **Coverage**: Must cover the entire optimization horizon

!!! info "Time Coverage"

If your horizon is 48 hours, forecast data must span at least 48 hours from the current time.

## How HAEO Handles Multiple Forecasts

When you configure multiple forecast sensors (e.g., today + tomorrow), HAEO automatically:

1. **Merges by time**: Combines forecasts into a single timeline
2. **Sums overlaps**: If multiple forecasts provide values for the same time, they are **summed**
3. **Fills gaps**: Uses linear interpolation between provided data points

### Example: Summing Forecasts

If you have two solar arrays providing separate forecasts:

```yaml
Forecast:
  - sensor.east_array_forecast # 3 kW at 12:00
  - sensor.west_array_forecast # 2 kW at 12:00
```

HAEO sums them: **5 kW total at 12:00**

!!! tip "Multiple Arrays"

    For solar systems, you can either:

    - Provide separate forecasts and let HAEO sum them
    - Combine forecasts yourself in a template sensor

    Both approaches work equally well.

### Example: Merging Time Ranges

For price forecasts split across days:

```yaml
Import Price:
  - sensor.price_today # Covers 00:00-23:59 today
  - sensor.price_tomorrow # Covers 00:00-23:59 tomorrow
```

HAEO merges them into a continuous 48-hour timeline.

## Supported Forecast Integrations

HAEO works with any integration that provides forecast attributes. Common integrations include:

### Solar Forecasts

- **[Open-Meteo Solar Forecast](https://github.com/rany2/ha-open-meteo-solar-forecast)** - Free, 7-day forecasts
- **[Solcast Solar](https://github.com/BJReplay/ha-solcast-solar)** - Professional solar forecasting

### Electricity Prices

- **[Amber Electric](https://www.home-assistant.io/integrations/amberelectric/)** - Australian real-time pricing (24h forecasts)
- **[Nordpool](https://www.home-assistant.io/integrations/nordpool/)** - European spot pricing
- **[Tibber](https://www.home-assistant.io/integrations/tibber/)** - Smart pricing in Europe

### Custom Forecasts

You can create custom forecast sensors using Home Assistant templates (see examples below).

## Creating Forecast Sensors with Templates

### Time-of-Use Tariff

For fixed pricing schedules that change by time of day:

```yaml
template:
  - sensor:
      - name: "Time of Use Import Price"
        unique_id: tou_import_price
        unit_of_measurement: "$/kWh"
        state: >
          {% set hour = now().hour %}
          {% if hour >= 16 and hour < 21 %}
            0.45
          {% elif hour >= 6 and hour < 16 or hour >= 21 %}
            0.25
          {% else %}
            0.15
          {% endif %}
        attributes:
          forecast: >
            {% set prices = {
              "off_peak": 0.15,
              "shoulder": 0.25,
              "peak": 0.45
            } %}
            {% set forecast_list = [] %}
            {% set start = now().replace(minute=0, second=0, microsecond=0) %}

            {# Generate 48 hours of forecast #}
            {% for day in range(2) %}
              {% for hour in range(24) %}
                {% set forecast_time = (start + timedelta(days=day, hours=hour)) %}
                {% set h = forecast_time.hour %}

                {# Determine price for this hour #}
                {% if h >= 16 and h < 21 %}
                  {% set price = prices.peak %}
                {% elif h >= 6 and h < 16 or h >= 21 %}
                  {% set price = prices.shoulder %}
                {% else %}
                  {% set price = prices.off_peak %}
                {% endif %}

                {# Add entry at start and end of period to prevent interpolation #}
                {% set entry_start = {
                  "datetime": forecast_time.isoformat(),
                  "value": price
                } %}
                {% set _ = forecast_list.append(entry_start) %}

                {% set entry_end = {
                  "datetime": (forecast_time + timedelta(hours=1, seconds=-1)).isoformat(),
                  "value": price
                } %}
                {% set _ = forecast_list.append(entry_end) %}
              {% endfor %}
            {% endfor %}

            {{ forecast_list }}
```

!!! info "Start and End Times"

    Providing entries at the start **and end** of each price block (one second before the next) prevents HAEO from interpolating between different price levels.

### Constant Price as Forecast

For a fixed price that doesn't change:

```yaml
template:
  - sensor:
      - name: "Constant Export Price"
        unique_id: constant_export_price
        unit_of_measurement: "$/kWh"
        state: "0.08"
        attributes:
          forecast: >
            {% set forecast_list = [] %}
            {% set start = now() %}
            {# Generate 48 hours with same price #}
            {% for hour in range(48) %}
              {% set forecast_time = start + timedelta(hours=hour) %}
              {% set entry = {
                "datetime": forecast_time.isoformat(),
                "value": 0.08
              } %}
              {% set _ = forecast_list.append(entry) %}
            {% endfor %}
            {{ forecast_list }}
```

### Simple Load Forecast

Based on historical averages by hour of day:

```yaml
template:
  - sensor:
      - name: "House Load Forecast"
        unique_id: house_load_forecast
        unit_of_measurement: "kW"
        state: >
          {% set hour = now().hour %}
          {# Define typical load by hour #}
          {% set hourly_load = {
            0: 0.8, 1: 0.7, 2: 0.7, 3: 0.7, 4: 0.8, 5: 1.2,
            6: 2.5, 7: 3.0, 8: 2.0, 9: 1.5, 10: 1.2, 11: 1.5,
            12: 2.0, 13: 1.8, 14: 1.5, 15: 1.8, 16: 2.5, 17: 3.5,
            18: 4.0, 19: 3.5, 20: 3.0, 21: 2.5, 22: 2.0, 23: 1.5
          } %}
          {{ hourly_load[hour] }}
        attributes:
          forecast: >
            {% set hourly_load = {
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
                "value": hourly_load[hour_of_day]
              } %}
              {% set _ = forecast_list.append(entry) %}
            {% endfor %}

            {{ forecast_list }}
```

## Troubleshooting Forecasts

### Forecasts Not Long Enough

**Problem**: Optimization fails with insufficient forecast data.

**Solution**: Ensure forecasts cover your entire horizon:

- 24-hour horizon needs ≥24 hours of forecast
- 48-hour horizon needs ≥48 hours of forecast

Check your integration's forecast length:

| Integration      | Typical Forecast Length |
| ---------------- | ----------------------- |
| Open-Meteo Solar | 7 days                  |
| Solcast          | 7 days                  |
| Amber Electric   | 24-30 hours             |
| Nordpool         | 24-36 hours             |
| Template sensors | As configured           |

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

Forecast sensors should update:

- **Prices**: Before each tariff change
- **Solar**: Every 1-6 hours
- **Load**: Every 1-6 hours

More frequent updates allow HAEO to adjust to changing conditions.

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

- [Grid Configuration](entities/grid.md) - Using price forecasts
- [Photovoltaics Configuration](entities/photovoltaics.md) - Using solar forecasts
- [Load Configuration](entities/loads.md) - Using load forecasts
- [Troubleshooting](troubleshooting.md#forecasts-are-not-long-enough) - Forecast issues

[:octicons-arrow-right-24: Continue to Entity Configuration](entities/index.md)
