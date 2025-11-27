# Load

Loads represent power consumption in your system.
The Load element uses forecast data to model any type of consumption pattern from fixed baseline loads to variable time-varying consumption.

## Configuration

| Field                     | Type                                     | Required | Default | Description                               |
| ------------------------- | ---------------------------------------- | -------- | ------- | ----------------------------------------- |
| **[Name](#name)**         | String                                   | Yes      | -       | Unique identifier for this load           |
| **[Forecast](#forecast)** | [sensor(s)](../forecasts-and-sensors.md) | Yes      | -       | Power consumption forecast sensor(s) (kW) |

## Name

Unique identifier for this load within your HAEO configuration.
Used to create sensor entity IDs and identify the load in connections.

**Examples**: "Base Load", "House Load", "Total Load", "EV Charger", "Pool Pump"

## Forecast

Specify one or more Home Assistant sensor entities providing power consumption data.
The Load element is flexible and works with both constant and time-varying patterns.

**Examples**:

```yaml
# Single forecast
Forecast: sensor.house_load_forecast

# Multiple load components
Forecast:
  - sensor.base_load
  - sensor.ev_charger_schedule
  - sensor.hvac_forecast
```

Provide all load forecasts to get accurate total consumption predictions.
See the [Forecasts and Sensors guide](../forecasts-and-sensors.md) for details on how HAEO processes sensor data.

## Constant Load Pattern

For fixed baseline consumption that doesn't vary over time, use an [input_number helper](https://www.home-assistant.io/integrations/input_number/) providing a constant value.

### Creating a Constant Load

1. **Create Input Number Helper**:

    - Go to Settings → Devices & Services → Helpers
    - Add a new "Number" helper
    - Set name: "Base Load Power"
    - Set unit: kW
    - Set desired constant value (e.g., 1.0)

2. **Configure Load Element**:

    | Field        | Value                        |
    | ------------ | ---------------------------- |
    | **Name**     | Base Load                    |
    | **Forecast** | input_number.base_load_power |

This configuration represents constant consumption (e.g., 1 kW = 24 kWh per day).

### Determining Your Baseline

To find your baseline consumption:

1. **Measure overnight minimum**: Check your consumption during hours when everything is "off" (e.g., 2-4 AM)
2. **Add always-on devices**: Include refrigerators, networking equipment, standby devices
3. **Add safety margin**: Increase by 10-20% to account for variations

### Typical Values

- **Small apartment**: 0.2-0.4 kW
- **Average home**: 0.5-1.2 kW
- **Large home**: 1.0-2.0 kW
- **Commercial**: 2.0+ kW

!!! tip "Start Conservative"

    It's better to overestimate baseline consumption slightly.
    The optimizer will ensure sufficient power is available.

## Forecast-Based Load Pattern

For variable consumption that changes over time, use sensors that provide forecast data.

### Single Variable Load

| Field        | Value                      |
| ------------ | -------------------------- |
| **Name**     | House Load                 |
| **Forecast** | sensor.house_load_forecast |

The forecast sensor should provide:

- Current consumption value
- Forecast data for future periods
- Unit of measurement: kW

### Common Forecast Sources

**Direct Measurement**:

- Home energy monitors
- Smart meters with forecast capability
- Utility consumption APIs

**Calculated Forecasts**:

- Template sensors combining multiple sources
- Machine learning predictions
- Historical pattern averaging

**Scheduled Devices**:

- EV charger schedules
- Pool pump timers
- HVAC duty cycles

## Combining Constant and Variable Loads

For most accurate optimization, combine a constant baseline with variable consumption:

**Configuration 1: Constant baseline**

| Field        | Value                        |
| ------------ | ---------------------------- |
| **Name**     | Base Load                    |
| **Forecast** | input_number.base_load_power |

**Configuration 2: Variable consumption on top**

| Field        | Value                       |
| ------------ | --------------------------- |
| **Name**     | Variable Load               |
| **Forecast** | sensor.variable_consumption |

Total consumption = 1.0 kW (constant) + variable forecast.

This approach:

- Simplifies forecast creation (only forecast variable portion)
- Ensures baseline is always covered
- Improves optimization reliability
- Makes it easier to adjust baseline without changing forecasts

## Combining Loads

Combine multiple load sources in a single element:

| Field        | Value                                                                                               |
| ------------ | --------------------------------------------------------------------------------------------------- |
| **Name**     | Total House Load                                                                                    |
| **Forecast** | input_number.base_load, sensor.ev_charger_schedule, sensor.pool_pump_schedule, sensor.hvac_forecast |

HAEO automatically sums all sensors at each timestamp, allowing you to model complex load profiles from simple components.

## Configuration Examples

### Simple Constant Load

Fixed baseline consumption:

| Field        | Value                       |
| ------------ | --------------------------- |
| **Name**     | Base Load                   |
| **Forecast** | input_number.constant_power |

### Variable Household Consumption

Time-varying consumption with forecast:

| Field        | Value                             |
| ------------ | --------------------------------- |
| **Name**     | House Load                        |
| **Forecast** | sensor.house_consumption_forecast |

### Combined Constant and Variable

Baseline plus variable components:

| Field        | Value                                                  |
| ------------ | ------------------------------------------------------ |
| **Name**     | Total Load                                             |
| **Forecast** | input_number.baseline_power, sensor.appliance_forecast |

### Multiple Variable Sources

Combine multiple consumption sources:

| Field        | Value                                                                                     |
| ------------ | ----------------------------------------------------------------------------------------- |
| **Name**     | All Loads                                                                                 |
| **Forecast** | sensor.base_consumption, sensor.ev_charger, sensor.pool_pump_schedule, sensor.hvac_system |

## Sensors Created

These sensors provide visibility into load power consumption and the marginal cost of serving the load.

| Sensor                                                    | Unit  | Description                        |
| --------------------------------------------------------- | ----- | ---------------------------------- |
| [`sensor.{name}_power_consumed`](#power-consumed)         | kW    | Power consumed by load             |
| [`sensor.{name}_load_power_balance`](#load-power-balance) | \$/kW | Marginal cost of serving this load |

### Power Consumed

The optimal power consumed by this load at each time period.

Since loads are not controllable in HAEO, this value matches the forecast or constant value provided in the configuration.
The optimization determines how to supply this power (from grid, battery, or solar), but the load consumption itself is fixed.

**For constant loads**: The sensor shows the same value for all periods (the configured constant power).

**For variable loads**: The sensor reflects the forecast values for each period from the configured sensor(s).

**Example**: A value of 2.5 kW means this load requires 2.5 kW at this time period, which the optimization must supply from available sources.

### Load Power Balance

The marginal cost of supplying power to this load at each time period.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price represents the cost of the most expensive power source needed to satisfy this load.
It reflects what it costs the system to deliver 1 kW to this load location.

**Interpretation**:

- **Positive value**: Represents the cost of serving this load (typically grid import price when importing)
- **Higher values**: Indicate serving the load is expensive (peak grid prices, battery constraints, etc.)
- **Lower values**: Indicate serving the load is cheap (off-peak prices, excess solar, etc.)
- **Magnitude**: Shows the economic pressure at this load point in the network

**Example**: A value of 0.28 means it costs \$0.28 per kW to serve this load at this time period, reflecting the marginal cost of the power source.

---

All sensors include a `forecast` attribute containing future optimized values for upcoming periods.
For constant loads, the forecast shows the same value for all periods.
For variable loads, the forecast reflects the configured sensor forecast values.

## Troubleshooting

### Sensor Not Found

**Problem**: Error "Sensors not found or unavailable"

**Solutions**:

- Verify sensor entity ID exists in Home Assistant
- Check sensor is available (not "unavailable" or "unknown")
- Ensure sensor provides numeric values
- For input_number helpers, ensure they are created and have a value set

### Incorrect Load Values

**Problem**: Load values don't match expectations

**Check**:

1. **Units**: Ensure sensor reports power in kW (not W or MW)
2. **Multiple sensors**: Verify you want additive combination
3. **Constant vs Variable**: Confirm sensor type matches intent
4. **Forecast data**: Check sensor attributes contain forecast if expected

### Optimization Infeasible

If optimization fails with loads:

1. **Check total load vs supply**: Ensure grid + solar + battery can supply the total load
2. **Verify load values**: Check that load power is reasonable
3. **Grid limits**: Ensure grid import limit is sufficient for load
4. **Constant load too high**: If using constant load, verify it's within available power

### Load Too Low

**Problem**: Optimizer shows lower consumption than expected

**Cause**: Loads in HAEO represent required consumption that must be met.
If your forecast includes optional or deferrable loads, the optimizer may schedule them differently.

**Solution**: Only include loads that represent actual required consumption in the Load element.
For controllable/deferrable loads, model them separately with appropriate constraints.

## Next Steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connect to network**

    ---

    Learn how to connect your load to other elements using connections.

    [:material-arrow-right: Connections guide](connections.md)

- :material-chart-line:{ .lg .middle } **Configure forecast sensors**

    ---

    Deep dive into how HAEO loads and processes sensor data.

    [:material-arrow-right: Forecasts and sensors](../forecasts-and-sensors.md)

- :material-battery-charging:{ .lg .middle } **Add battery storage**

    ---

    Pair loads with battery storage to optimize energy usage.

    [:material-arrow-right: Battery configuration](battery.md)

- :material-transmission-tower:{ .lg .middle } **Add grid connection**

    ---

    Configure grid import/export to meet load requirements.

    [:material-arrow-right: Grid configuration](grid.md)

</div>
