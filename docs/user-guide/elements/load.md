# Load

Loads represent power consumption in your system.
The Load element uses forecast data to model any type of consumption pattern from fixed baseline loads to variable time-varying consumption.

!!! note "Connection endpoints"

    Load elements appear in connection selectors only when Advanced Mode is enabled on your hub.

## Configuration

| Field                                       | Type                                     | Required | Default  | Description                                                                 |
| ------------------------------------------- | ---------------------------------------- | -------- | -------- | --------------------------------------------------------------------------- |
| **[Name](#name)**                           | String                                   | Yes      | -        | Unique identifier for this load                                             |
| **[Forecast](#forecast)**                   | [sensor(s)](../forecasts-and-sensors.md) | Yes      | -        | Power consumption forecast sensor(s) (kW)                                   |
| **[Consumption value](#consumption-value)** | Number (\$/kWh)                          | No       | Disabled | Value per kWh of this load when it runs                                     |
| **[Shedding](#shedding)**                   | Boolean                                  | No       | false    | Allow the optimizer to reduce load below the forecast when it is uneconomic |

## Name

Unique identifier for this load within your HAEO configuration.
Used to create sensor entity IDs and identify the load in connections.

**Examples**: "Base Load", "House Load", "Total Load", "EV Charger", "Pool Pump"

## Forecast

Specify one or more Home Assistant sensor entities providing power consumption data.
The Load element is flexible and works with both constant and time-varying patterns.

**Single forecast example**:

| Field        | Value                      |
| ------------ | -------------------------- |
| **Forecast** | sensor.house_load_forecast |

**Multiple load components example**:

| Field        | Value                                                              |
| ------------ | ------------------------------------------------------------------ |
| **Forecast** | sensor.base_load, sensor.ev_charger_schedule, sensor.hvac_forecast |

Provide all load forecasts to get accurate total consumption predictions.
See the [Forecasts and Sensors guide](../forecasts-and-sensors.md) for details on how HAEO processes sensor data.

## Consumption value

Optional value per kWh of this load when it is running.
This is used only when [Shedding](#shedding) is enabled.

**Default**: Disabled.

**How to choose a value**:

- Use a higher value for loads you strongly prefer to keep on.
- Use a lower value for loads you are comfortable shedding during expensive periods.

!!! tip "Why this matters"

    If shedding is enabled and no value is set, the optimizer will usually shed the load because supplying power has a cost.

## Shedding

Allow HAEO to reduce load consumption below the forecast.

**Default**: Disabled (load follows the forecast exactly).

**When enabled**: HAEO can shed the load when supplying energy is more expensive than the configured [Consumption value](#consumption-value).

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
- [Historical pattern averaging](../historical-load-forecast.md)

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

### Input Entities

Each configuration field creates a corresponding input entity in Home Assistant.
Input entities appear as Number or Switch entities with the `config` entity category.

| Input                               | Unit   | Description                                    |
| ----------------------------------- | ------ | ---------------------------------------------- |
| `number.{name}_forecast`            | kW     | Load power forecast from configured sensor(s)  |
| `number.{name}_price_target_source` | \$/kWh | Consumption value from configured value/sensor |
| `switch.{name}_curtailment`         | -      | Whether shedding is permitted                  |

Input entities include a `forecast` attribute showing values for each optimization period.
See the [Input Entities developer guide](../../developer-guide/inputs.md) for details on input entity behavior.

## Sensors Created

### Sensor Summary

A Load element creates 1 device in Home Assistant with the following sensors.

| Sensor                                                        | Unit  | Description                                     |
| ------------------------------------------------------------- | ----- | ----------------------------------------------- |
| [`sensor.{name}_power`](#power)                               | kW    | Power consumed by load                          |
| [`sensor.{name}_forecast_limit_price`](#forecast-limit-price) | \$/kW | Shadow price of the load power limit constraint |

### Power

The optimal power consumed by this load at each time period.

When [Shedding](#shedding) is disabled, this matches the configured forecast or constant value.
When shedding is enabled, this may be lower than the forecast if the optimizer determines shedding reduces total system cost.

**For constant loads**: The sensor shows the same value for all periods (the configured constant power).

**For variable loads**: The sensor reflects the forecast values for each period from the configured sensor(s).

**Example**: A value of 2.5 kW means this load requires 2.5 kW at this time period, which the optimization must supply from available sources.

### Forecast Limit Price

Shadow price of the load power limit constraint at each time period.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This reflects the marginal impact of increasing the allowed load power by 1 kW for the time period.
When shedding is disabled (fixed forecast), it is commonly interpreted as the marginal cost of serving the load.

**Interpretation**:

- **Positive value**: Increasing allowed load would increase total cost (power is expensive or constrained)
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

**Common causes**:

- Shedding is enabled and the [Consumption value](#consumption-value) is low (or disabled), so the optimizer prefers to shed the load.
- Your forecast includes optional or deferrable load that you expect to be scheduled, not modeled as always-on consumption.

**Solutions**:

- Disable [Shedding](#shedding) for loads that must always run.
- Set an appropriate [Consumption value](#consumption-value) for loads that can be shed but are still valuable.
- Only include loads that represent required consumption in the Load element.
    For controllable/deferrable loads, model them separately with appropriate constraints.

## Next Steps

<div class="grid cards" markdown>

- :material-history:{ .lg .middle } **Create a historical load forecast**

    ---

    Build a simple load forecast from past consumption data.

    [:material-arrow-right: Historical load forecast](../historical-load-forecast.md)

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
