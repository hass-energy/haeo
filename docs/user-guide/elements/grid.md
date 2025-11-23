# Grid Configuration

The grid represents your connection to the electricity network.
It allows bidirectional power flow: importing (buying) and exporting (selling) electricity.

## Configuration Fields

| Field            | Type                                     | Required | Default | Description                            |
| ---------------- | ---------------------------------------- | -------- | ------- | -------------------------------------- |
| **Name**         | String                                   | Yes      | -       | Unique identifier                      |
| **Import Price** | [sensor(s)](../forecasts-and-sensors.md) | Yes      | -       | Price per kWh for importing (\$/kWh)   |
| **Export Price** | [sensor(s)](../forecasts-and-sensors.md) | Yes      | -       | Revenue per kWh for exporting (\$/kWh) |
| **Import Limit** | Number (kW)                              | No       | -       | Maximum import power                   |
| **Export Limit** | Number (kW)                              | No       | -       | Maximum export power                   |

## Import Price

Specify one or more Home Assistant sensors providing electricity import pricing.

### Single Sensor

```yaml
Import Price: sensor.electricity_import_price
```

HAEO reads the sensor's current value and any forecast data.
A single value repeats across the optimization horizon.
Forecast data is interpolated for each optimization period.

### Multiple Sensors

Combine multiple price sources or time periods:

```yaml
Import Price:
  - sensor.electricity_price_today
  - sensor.electricity_price_tomorrow
```

HAEO combines multiple sensors by summing their values at each timestamp.
This is useful for:

- Splitting today and tomorrow forecasts
- Combining wholesale and retail components
- Adding time-of-use and demand charges

### How It Works

See the [Forecasts and Sensors guide](../forecasts-and-sensors.md) for complete details on:

- How HAEO extracts present values and forecasts
- Interpolation between forecast points
- Combining multiple sensors
- Creating custom price forecast sensors

## Export Price

Specify one or more Home Assistant sensors providing electricity export pricing.

Configuration works the same as Import Price (single or multiple sensors).

**Typical relationship**: Export price is usually lower than import price.

- Import: \$0.25/kWh (what you pay to buy)
- Export: \$0.10/kWh (what you receive to sell)

This price difference incentivizes self-consumption and strategic battery usage.

**Important**: Ensure export price < import price to prevent unrealistic arbitrage in optimization.

## Import Limit

Maximum power that can be imported from the grid (kW).

**Optional** - if not specified, import is unlimited.

Use this to model:

- Main breaker capacity
- Grid connection limits
- Fuse ratings

**Example**: `15` for 15 kW maximum import

## Export Limit

Maximum power that can be exported to the grid (kW).

**Optional** - if not specified, export is unlimited.

Use this to model:

- Inverter export limits
- Grid connection agreements
- Feed-in tariff restrictions

**Example**: `10` for 10 kW maximum export

## Configuration Example

Dynamic pricing with forecast sensors:

```yaml
Name: Main Grid
Import Price:
  - sensor.electricity_import_today
  - sensor.electricity_import_tomorrow
Export Price:
  - sensor.electricity_export_today
  - sensor.electricity_export_tomorrow
Import Limit: 15
Export Limit: 10
```

Fixed pricing configuration:

```yaml
Name: Grid Connection
Import Price: sensor.fixed_import_price  # Single sensor (e.g., input_number or template sensor)
Export Price: sensor.fixed_export_price
Import Limit: 20
Export Limit: 5
```

For more examples, see the [Forecasts and Sensors guide](../forecasts-and-sensors.md).

## Sensors Created

| Sensor                         | Unit   | Description                                |
| ------------------------------ | ------ | ------------------------------------------ |
| `sensor.{name}_power_imported` | kW     | Power imported from grid (positive values) |
| `sensor.{name}_power_exported` | kW     | Power exported to grid (positive values)   |
| `sensor.{name}_price_import`   | \$/kWh | Import price for current period            |
| `sensor.{name}_price_export`   | \$/kWh | Export price for current period            |

After optimization completes, sensors show values for the current optimization period.
The `forecast` attribute on each sensor contains future values for upcoming periods.

## Troubleshooting

### Sensor Not Found

**Problem**: Error "Sensors not found or unavailable"

**Solutions**:

- Verify sensor entity IDs exist in Home Assistant
- Check sensors are available (not "unavailable" or "unknown")
- Ensure pricing integration is configured correctly
- Verify sensors have appropriate device class (e.g., `monetary` for prices)

### Incorrect Price Values

**Problem**: Price values don't match expectations

**Check**:

- Sensor units match HAEO expectations (uses Home Assistant's native currency units)
- Multiple sensors sum correctly (intended?)
- Forecast data quality from source
- Import price > export price (prevents arbitrage)

### Grid Not Optimizing

**Problem**: Grid always imports or never responds to price changes

**Possible causes**:

- Prices are constant (no optimization needed)
- Battery at SOC limits
- Grid not connected to other elements
- Load exceeds available supply

**Solutions**:

- Verify price sensors provide varying values
- Check battery SOC limits and capacity
- Review connections in network configuration
- Check grid import limit vs total load

## Next Steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connect to network**

    ---

    Learn how to connect your grid to other elements using connections.

    [:material-arrow-right: Connections guide](connections.md)

- :material-chart-line:{ .lg .middle } **Configure price sensors**

    ---

    Deep dive into how HAEO uses electricity pricing for optimization.

    [:material-arrow-right: Forecasts and sensors](../forecasts-and-sensors.md)

- :material-battery-charging:{ .lg .middle } **Add battery storage**

    ---

    Store cheap grid energy during off-peak hours for use during expensive periods.

    [:material-arrow-right: Battery configuration](battery.md)

- :material-math-integral:{ .lg .middle } **Grid modeling**

    ---

    Understand the mathematical formulation of grid optimization.

    [:material-arrow-right: Grid modeling](../../modeling/grid.md)

</div>
