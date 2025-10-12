# Sensor Type Reference

Complete reference for all sensor types created by HAEO with examples and usage patterns.

## Overview

HAEO creates two categories of sensors:

- **Network sensors**: Overall optimization results (one set per HAEO integration)
- **Entity sensors**: Per-entity optimization results (one set per configured entity)

All sensors include:

- **Current state**: Optimal value for the current/first period
- **Forecast attribute**: Array of future optimal values with timestamps
- **Automatic updates**: Refresh every optimization cycle (default: 5 minutes)

## Network Sensors

Created once per HAEO integration to expose overall optimization results.

### Optimization Cost

**Entity ID**: `sensor.{network}_optimization_cost`

**Unit**: $ (dollars)

**Description**: Total cost over the entire optimization horizon

**Interpretation**:

- **Positive value**: Net cost (spending exceeds revenue)
- **Zero**: Break-even (spending equals revenue)
- **Negative value**: Net revenue (revenue exceeds spending)

**Example**:

```yaml
sensor.main_network_optimization_cost:
  state: 12.45
  unit_of_measurement: "$"
  device_class: monetary
```

**Usage in automations**:

```yaml
automation:
  - alias: "Alert High Energy Cost"
    trigger:
      platform: numeric_state
      entity_id: sensor.main_network_optimization_cost
      above: 20
    action:
      service: notify.mobile_app
      data:
        message: "Today's energy cost forecast: ${{ states('sensor.main_network_optimization_cost') }}"
```

### Optimization Status

**Entity ID**: `sensor.{network}_optimization_status`

**Unit**: None

**Description**: Result status of most recent optimization

**Possible values**:

- `optimal`: Optimal solution found
- `feasible`: Feasible but not proven optimal (rare)
- `infeasible`: No solution satisfies all constraints
- `failed`: Solver error or timeout
- `unknown`: Not yet run

**Example**:

```yaml
sensor.main_network_optimization_status:
  state: "optimal"
```

**Usage in automations**:

```yaml
automation:
  - alias: "Alert Optimization Failure"
    trigger:
      platform: state
      entity_id: sensor.main_network_optimization_status
      to: "failed"
    action:
      service: notify.admin
      data:
        message: "HAEO optimization failed - check configuration"
```

### Optimization Duration

**Entity ID**: `sensor.{network}_optimization_duration`

**Unit**: seconds

**Description**: Time taken to solve most recent optimization

**Typical values**:

- 0.1-0.5s: Small systems (few entities, short horizon)
- 0.5-2s: Medium systems (typical home setup)
- 2-10s: Large systems (multiple batteries, buildings)

**Example**:

```yaml
sensor.main_network_optimization_duration:
  state: 1.23
  unit_of_measurement: "s"
```

**Usage for monitoring**:

```yaml
automation:
  - alias: "Monitor Optimization Performance"
    trigger:
      platform: numeric_state
      entity_id: sensor.main_network_optimization_duration
      above: 5
    action:
      service: persistent_notification.create
      data:
        message: "Optimization taking longer than usual: {{ states('sensor.main_network_optimization_duration') }}s"
```

## Entity Sensors

Created for each configured entity to expose its optimal power/energy values.

### Power Sensors

**Entity ID**: `sensor.{entity}_power`

**Unit**: kW (kilowatts)

**Description**: Optimal power flow for the entity

**Sign conventions by entity type**:

| Entity Type      | Positive Value            | Negative Value          |
| ---------------- | ------------------------- | ----------------------- |
| **Battery**      | Discharging               | Charging                |
| **Grid**         | Importing (from grid)     | Exporting (to grid)     |
| **Photovoltaics**| Generating                | Never negative          |
| **Load**         | Consuming                 | Never negative          |

**Battery example**:

```yaml
sensor.home_battery_power:
  state: 3.2  # Discharging at 3.2 kW
  unit_of_measurement: "kW"
  device_class: power
  attributes:
    forecast:
      - datetime: "2025-10-12T10:00:00+00:00"
        value: 3.2
      - datetime: "2025-10-12T10:05:00+00:00"
        value: 2.8
      # ... more values
```

**Grid example**:

```yaml
sensor.main_grid_power:
  state: -2.5  # Exporting 2.5 kW to grid
  unit_of_measurement: "kW"
  device_class: power
```

**Usage in dashboards**:

```yaml
# Lovelace card
type: entities
entities:
  - entity: sensor.home_battery_power
    name: "Battery Power"
  - entity: sensor.main_grid_power
    name: "Grid Power"
  - entity: sensor.rooftop_solar_power
    name: "Solar Generation"
```

**Usage in automations**:

```yaml
automation:
  - alias: "Battery Discharge Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.home_battery_power
      above: 4  # Discharging more than 4 kW
    action:
      service: notify.mobile_app
      data:
        message: "Battery discharging at {{ states('sensor.home_battery_power') }} kW"
```

### Energy Sensors (Batteries Only)

**Entity ID**: `sensor.{battery}_energy`

**Unit**: kWh (kilowatt-hours)

**Description**: Optimal energy level in battery at each time

**Range**: Between min and max SOC limits (e.g., 2-9 kWh for 10 kWh battery with 20-90% limits)

**Example**:

```yaml
sensor.home_battery_energy:
  state: 7.5  # Currently 7.5 kWh stored
  unit_of_measurement: "kWh"
  device_class: energy_storage
  attributes:
    forecast:
      - datetime: "2025-10-12T10:00:00+00:00"
        value: 7.5
      - datetime: "2025-10-12T10:05:00+00:00"
        value: 7.2  # Discharged 0.3 kWh (at 3.6 kW for 5 min)
```

**Usage in graphs**:

```yaml
type: history-graph
entities:
  - sensor.home_battery_energy
hours_to_show: 48
```

### SOC Sensors (Batteries Only)

**Entity ID**: `sensor.{battery}_soc`

**Unit**: % (percentage)

**Description**: Optimal state of charge (percentage of capacity)

**Range**: Between min and max SOC configuration (e.g., 20-90%)

**Calculation**: `SOC = (Energy / Capacity) × 100`

**Example**:

```yaml
sensor.home_battery_soc:
  state: 75  # 75% charged
  unit_of_measurement: "%"
  device_class: battery
  attributes:
    forecast:
      - datetime: "2025-10-12T10:00:00+00:00"
        value: 75
      - datetime: "2025-10-12T17:00:00+00:00"
        value: 25  # Will discharge to 25% by evening peak
```

**Usage in dashboard**:

```yaml
type: gauge
entity: sensor.home_battery_soc
min: 0
max: 100
severity:
  green: 60
  yellow: 30
  red: 20
```

**Usage in automations**:

```yaml
automation:
  - alias: "Low Battery Warning"
    trigger:
      platform: numeric_state
      entity_id: sensor.home_battery_soc
      below: 25
    action:
      service: notify.mobile_app
      data:
        message: "Battery low: {{ states('sensor.home_battery_soc') }}%"
```

## Forecast Attributes

All HAEO sensors include a `forecast` attribute containing future optimal values.

### Forecast Structure

```yaml
attributes:
  forecast:
    - datetime: "2025-10-12T10:00:00+00:00"  # ISO 8601 timestamp
      value: 5.2                              # Numeric value
    - datetime: "2025-10-12T10:05:00+00:00"
      value: 5.1
    # ... continues for entire horizon
```

**Properties**:

- **Length**: Number of periods in horizon (e.g., 576 for 48h with 5-min periods)
- **Spacing**: Equal to optimization period (e.g., 5 minutes)
- **Timezone**: UTC timestamps
- **First value**: Matches current sensor state

### Using Forecasts in Templates

**Get next hour's value**:

```yaml
template:
  - sensor:
      - name: "Battery Power Next Hour"
        state: >
          {% set fc = state_attr('sensor.home_battery_power', 'forecast') %}
          {% if fc and fc|length > 12 %}
            {{ fc[12].value }}  {# 12 periods = 1 hour at 5-min periods #}
          {% else %}
            unknown
          {% endif %}
        unit_of_measurement: "kW"
```

**Find peak export time**:

```yaml
template:
  - sensor:
      - name: "Peak Export Time"
        state: >
          {% set fc = state_attr('sensor.main_grid_power', 'forecast') %}
          {% set ns = namespace(max_export=0, max_time='') %}
          {% for item in fc %}
            {% if item.value < ns.max_export %}
              {% set ns.max_export = item.value %}
              {% set ns.max_time = item.datetime %}
            {% endif %}
          {% endfor %}
          {{ ns.max_time }}
```

### Using Forecasts in Apexcharts

```yaml
type: custom:apexcharts-card
series:
  - entity: sensor.home_battery_soc
    name: Battery SOC
    data_generator: |
      return entity.attributes.forecast.map((item) => {
        return [new Date(item.datetime).getTime(), item.value];
      });
graph_span: 48h
span:
  start: hour
```

## Sensor States and Meanings

### Valid States

**Numeric value**: Optimization result

- Represents optimal value for current period
- Updated every optimization cycle
- Available immediately after successful optimization

**Example**: `5.2` (kW), `72` (%), `12.45` ($)

### Unknown State

**Value**: `unknown`

**Causes**:

- Integration just started (optimization not yet run)
- Optimization recently failed
- Configuration changed (awaiting next cycle)

**Resolution**: Wait for next optimization cycle (typically 5 minutes)

### Unavailable State

**Value**: `unavailable`

**Causes**:

- Home Assistant restarted (temporary)
- Integration disabled
- Sensor entity removed

**Resolution**: Check integration status, restart Home Assistant if needed

## Sensor Update Timing

### Update Frequency

**Default**: Every 5 minutes (matches default optimization period)

**Configurable**: Via `period_minutes` configuration

**Process**:

1. Coordinator triggers update
2. Data loaded from sensors/forecasts
3. Optimization runs
4. All sensors update simultaneously
5. Next update scheduled

### First Update

**Timing**: Shortly after Home Assistant starts and integration loads

**Delay**: Typically 10-30 seconds to:

- Load configuration
- Initialize coordinator
- Fetch initial forecast data
- Run first optimization

### Failed Updates

**Behavior**: Sensors retain last successful state

**Duration**: Until next successful optimization

**Indication**: Check `optimization_status` sensor for failure reason

## Using Sensors in Automations

### Battery Management

```yaml
automation:
  - alias: "Battery Charge During Off-Peak"
    trigger:
      platform: time_pattern
      hours: "/1"  # Check hourly
    condition:
      # Only during predicted charging periods
      - condition: numeric_state
        entity_id: sensor.home_battery_power
        below: -0.5  # Charging (negative)
    action:
      service: notify.mobile_app
      data:
        message: "Battery charging at {{ states('sensor.home_battery_power') }} kW"
```

### Export Maximization

```yaml
automation:
  - alias: "High Export Notification"
    trigger:
      platform: numeric_state
      entity_id: sensor.main_grid_power
      below: -5  # Exporting more than 5 kW
    action:
      service: notify.home
      data:
        message: "Exporting {{ states('sensor.main_grid_power')|abs }} kW to grid"
```

### Cost Monitoring

```yaml
automation:
  - alias: "Daily Cost Summary"
    trigger:
      platform: time
      at: "22:00:00"
    action:
      service: notify.mobile_app
      data:
        message: >
          Today's energy cost: ${{ states('sensor.main_network_optimization_cost') }}
          Battery used: {{ states('sensor.home_battery_power') }} kW
```

## Using Sensors in Dashboards

### Energy Dashboard

```yaml
type: vertical-stack
cards:
  - type: entity
    entity: sensor.main_network_optimization_cost
    name: "Total Cost"
    icon: mdi:currency-usd

  - type: entities
    entities:
      - entity: sensor.main_grid_power
        name: "Grid"
      - entity: sensor.rooftop_solar_power
        name: "Solar"
      - entity: sensor.home_battery_power
        name: "Battery"
      - entity: sensor.house_load_power
        name: "Load"

  - type: gauge
    entity: sensor.home_battery_soc
    name: "Battery SOC"
    min: 0
    max: 100
```

### Forecast Visualization

```yaml
type: custom:apexcharts-card
header:
  title: "48-Hour Energy Forecast"
series:
  - entity: sensor.home_battery_soc
    name: "Battery SOC"
    data_generator: |
      return entity.attributes.forecast.map((item) => {
        return [new Date(item.datetime).getTime(), item.value];
      });

  - entity: sensor.main_grid_power
    name: "Grid Power"
    data_generator: |
      return entity.attributes.forecast.map((item) => {
        return [new Date(item.datetime).getTime(), item.value];
      });

graph_span: 48h
```

## Historical Data and Statistics

### Long-Term Recorder

Sensors automatically store historical data via Home Assistant recorder.

**Configure retention**:

```yaml
# configuration.yaml
recorder:
  db_url: !secret database_url
  purge_keep_days: 30
  include:
    entities:
      - sensor.main_network_optimization_cost
      - sensor.home_battery_soc
      - sensor.main_grid_power
```

### Statistics Integration

Energy sensors support Home Assistant's energy dashboard:

```yaml
# Energy dashboard configuration
energy:
  sensors:
    - entity_id: sensor.main_grid_power
      name: "Grid Import/Export"
```

### Creating Utility Meters

Track daily/monthly totals:

```yaml
utility_meter:
  daily_energy_cost:
    source: sensor.main_network_optimization_cost
    cycle: daily

  monthly_battery_usage:
    source: sensor.home_battery_power
    cycle: monthly
```

## Troubleshooting Sensors

### Sensors Showing Unknown

1. Check `optimization_status` sensor
2. Verify integration is running
3. Check logs for optimization errors
4. Wait for next update cycle

### Sensors Not Updating

1. Verify coordinator is running
2. Check Home Assistant logs
3. Restart integration
4. Check forecast data availability

### Incorrect Sensor Values

1. Verify configuration is correct
2. Check input sensor/forecast accuracy
3. Review network topology
4. Validate constraints are realistic

## Related Documentation

- [Entity Reference](entities.md) - What entities create which sensors
- [Configuration Guide](../user-guide/configuration.md) - Setting up HAEO
- [Battery Configuration](../user-guide/entities/battery.md) - Battery sensor details
- [Grid Configuration](../user-guide/entities/grid.md) - Grid sensor details
- [Troubleshooting](../user-guide/troubleshooting.md) - Common sensor issues

## Next Steps

- Explore sensor states in Home Assistant developer tools
- Create dashboard cards using HAEO sensors
- Set up automations based on optimization results
- Monitor historical trends via Energy dashboard

[:octicons-arrow-right-24: Return to Reference Index](index.md)
