# Solar

Solar panels that generate electricity.
HAEO optimizes how generated power flows through your energy network.

!!! note "Connection endpoints"

    Solar elements appear in connection selectors only when Advanced Mode is enabled on your hub.

## Configuration

| Field                                     | Type                                     | Required | Default | Description                                                     |
| ----------------------------------------- | ---------------------------------------- | -------- | ------- | --------------------------------------------------------------- |
| **[Name](#name)**                         | String                                   | Yes      | -       | Unique identifier for this solar system                         |
| **[Forecast](#forecast)**                 | [sensor(s)](../forecasts-and-sensors.md) | Yes      | -       | Solar generation forecast sensor(s) providing power output (kW) |
| **[Production Price](#production-price)** | Number (\$/kWh)                          | No       | 0       | Cost or value per kWh of electricity generated                  |
| **[Curtailment](#curtailment)**           | Boolean                                  | No       | true    | Allow optimizer to reduce generation below forecast             |

## Name

Unique identifier for this solar system within your HAEO configuration.
Used to create sensor entity IDs and identify the solar array in connections.

**Examples**: "Rooftop Solar", "East Array", "West Array", "Combined Solar"

## Forecast

Specify one or more Home Assistant sensors providing solar generation data.

**Single array example**:

| Field        | Value                      |
| ------------ | -------------------------- |
| **Forecast** | sensor.solcast_pv_forecast |

**Multiple arrays example** (e.g., different orientations):

| Field        | Value                                                  |
| ------------ | ------------------------------------------------------ |
| **Forecast** | sensor.solar_east_forecast, sensor.solar_west_forecast |

Provide all solar array forecasts to get accurate total generation predictions.
See the [Forecasts and Sensors guide](../forecasts-and-sensors.md) for details on how HAEO processes sensor data.

## Production Price

Cost or value per kWh of electricity generated.

**Default**: Leave empty for zero cost (most common case)

**When to use non-zero values**:

- Modeling opportunity cost of generation
- Accounting for maintenance costs per kWh
- Rare specialized scenarios

!!! note

    Production price is NOT the same as export price.
    Export revenue is configured on the Grid element.

## Curtailment

Allow HAEO to reduce generation below the forecast level.

**Default**: Enabled (HAEO can curtail generation when beneficial)

**When enabled**: HAEO can curtail generation if:

- Export prices are negative (paying to export)
- Export limit is reached
- Battery is full and loads are satisfied

**When disabled**: Generation follows forecast exactly (useful when inverter cannot be controlled)

**Requirements**:

- Inverter must support active power limiting
- Control mechanism must be implemented separately (HAEO only optimizes)

## Configuration Examples

### Basic Configuration

Single solar array with forecast:

| Field                | Value                      |
| -------------------- | -------------------------- |
| **Name**             | Rooftop Solar              |
| **Forecast**         | sensor.solcast_pv_forecast |
| **Production Price** | 0                          |
| **Curtailment**      | false                      |

### Multiple Arrays

Combine multiple solar arrays or forecast sources:

| Field                | Value                                                  |
| -------------------- | ------------------------------------------------------ |
| **Name**             | Combined Solar                                         |
| **Forecast**         | sensor.east_array_forecast, sensor.west_array_forecast |
| **Production Price** | 0                                                      |
| **Curtailment**      | true                                                   |

### Input Entities

Each configuration field creates a corresponding input entity in Home Assistant.
Input entities appear as Number or Switch entities with the `config` entity category.

| Input                               | Unit   | Description                                    |
| ----------------------------------- | ------ | ---------------------------------------------- |
| `number.{name}_forecast`            | kW     | Solar power forecast from configured sensor(s) |
| `number.{name}_price_source_target` | \$/kWh | Production price from configured value/sensor  |
| `switch.{name}_curtailment`         | -      | Whether curtailment is permitted               |

Input entities include a `forecast` attribute showing values for each optimization period.
See the [Input Entities developer guide](../../developer-guide/inputs.md) for details on input entity behavior.

## Sensors Created

### Sensor Summary

A Solar element creates 1 device in Home Assistant with the following sensors.

| Sensor                                              | Unit  | Description                             |
| --------------------------------------------------- | ----- | --------------------------------------- |
| [`sensor.{name}_power`](#power)                     | kW    | Actual power generated                  |
| [`sensor.{name}_power_available`](#power-available) | kW    | Maximum available solar power           |
| [`sensor.{name}_forecast_limit`](#forecast-limit)   | \$/kW | Value of additional generation capacity |

All sensors include a `forecast` attribute containing future optimized values for upcoming periods.

### Sensor Details Power

The optimal power generated by the solar array at each time period after any curtailment decisions.

This represents the actual power output from the solar system.
When curtailment is disabled, this equals the available power from the forecast.
When curtailment is enabled, this may be less than available power if the optimizer determines curtailing generation reduces total system cost.

**Example**: A value of 4.2 kW means the solar array is producing 4.2 kW at this time period.

### Power Available

The maximum solar power available from the forecast before any curtailment.

This represents what the solar array could produce based on weather forecasts and system capacity.
It serves as the upper limit for actual generation.
The difference between `power_available` and `power` shows how much generation is being curtailed.

**Example**: A value of 5.0 kW when `power` is 4.2 kW means 0.8 kW of solar generation is being curtailed at this time.

### Forecast Limit

The marginal value of additional generation capacity.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would change if the solar forecast were increased by 1 kW at this time period.
It indicates whether more solar generation would be beneficial or detrimental.

**Interpretation**:

- **Zero value**: Not curtailing generation (using all available solar power)
- **Positive value**: System would benefit from more solar generation
    - More generation would reduce total system cost
    - If curtailing, suggests curtailment may be too aggressive
- **Negative value**: System is better off with less solar generation
    - Curtailing generation reduces total system cost
    - Typically occurs when export prices are negative or battery is full with nowhere for energy to go
    - More negative values indicate curtailing more aggressively would further reduce costs

**Example**: A value of -0.10 means that if the solar forecast were 1 kW higher, the total system cost would increase by \$0.10 at this time period, indicating that curtailing generation is economically beneficial.

## Troubleshooting

### Sensor Not Found

**Problem**: Error "Sensors not found or unavailable"

**Solutions**:

- Verify sensor entity ID exists in Home Assistant
- Check sensor is available (not "unavailable" or "unknown")
- Ensure solar forecast integration is configured correctly

### Incorrect Generation Values

**Problem**: Generation values don't match expectations

**Check**:

- Sensor units are kW (not W or kWh)
- Multiple sensors sum correctly (intended?)
- Forecast integration is providing realistic data
- System size configured correctly in forecast integration

### No Generation in Optimization

**Problem**: Optimization shows zero solar generation

**Possible causes**:

- Forecast covers wrong time period (nighttime only)
- Sensor values are zero due to weather
- Forecast data format not recognized

**Solutions**:

- Check sensor forecast attribute in Developer Tools → States
- Verify forecast covers daytime hours
- Review HAEO logs for format detection warnings

## Next Steps

<div class="grid cards" markdown>

- :material-solar-power:{ .lg .middle } **Connect to network**

    ---

    Learn how to connect your solar to other elements using connections.

    [:material-arrow-right: Connections guide](connections.md)

- :material-chart-line:{ .lg .middle } **Understand sensor loading**

    ---

    Deep dive into how HAEO uses forecast data for solar optimization.

    [:material-arrow-right: Forecasts and sensors](../forecasts-and-sensors.md)

- :material-battery-charging:{ .lg .middle } **Add battery storage**

    ---

    Store excess solar generation for use during peak pricing or nighttime.

    [:material-arrow-right: Battery configuration](battery.md)

</div>
