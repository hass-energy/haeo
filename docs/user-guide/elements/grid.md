# Grid

The grid represents your connection to the electricity network.
It allows bidirectional power flow: importing (buying) and exporting (selling) electricity.

## Configuration

| Field                             | Type                                     | Required | Default | Description                                                |
| --------------------------------- | ---------------------------------------- | -------- | ------- | ---------------------------------------------------------- |
| **[Name](#name)**                 | String                                   | Yes      | -       | Unique identifier for this grid connection                 |
| **[Import Price](#import-price)** | [sensor(s)](../forecasts-and-sensors.md) | Yes      | -       | Price per kWh for importing electricity from grid (\$/kWh) |
| **[Export Price](#export-price)** | [sensor(s)](../forecasts-and-sensors.md) | Yes      | -       | Revenue per kWh for exporting electricity to grid (\$/kWh) |
| **[Import Limit](#import-limit)** | Number (kW)                              | No       | -       | Maximum import power from grid                             |
| **[Export Limit](#export-limit)** | Number (kW)                              | No       | -       | Maximum export power to grid                               |

## Name

Unique identifier for this grid connection within your HAEO configuration.
Used to create sensor entity IDs and identify the grid in connections.

**Examples**: "Main Grid", "Grid Connection", "Utility"

## Import Price

Specify one or more Home Assistant sensors providing electricity import pricing.

**Sign convention**: Import prices should be positive numbers representing the cost you pay to buy electricity from the grid.
For example, `0.25` means you pay \$0.25 per kWh imported.

**Examples**:

```yaml
# Single sensor
Import Price: sensor.electricity_import_price

# Multiple sensors (today and tomorrow forecasts)
Import Price:
  - sensor.electricity_price_today
  - sensor.electricity_price_tomorrow
```

Provide all relevant price sensors (today, tomorrow, etc.) to ensure complete horizon coverage.
See the [Forecasts and Sensors guide](../forecasts-and-sensors.md) for details on how HAEO processes sensor data.

## Export Price

Specify one or more Home Assistant sensors providing electricity export pricing.
Provide all relevant price sensors to ensure complete horizon coverage.

**Sign convention**: Export prices should be positive numbers representing the revenue you receive for selling electricity to the grid.
For example, `0.10` means you receive \$0.10 per kWh exported.

**Typical relationship**: Export price is usually lower than import price.

- Import: \$0.25/kWh (what you pay to buy)
- Export: \$0.10/kWh (what you receive to sell)

This price difference incentivizes self-consumption and strategic battery usage.

**Negative export prices**: When the grid operator charges you to export use negative values.
For example, `-0.05` means you pay \$0.05 per kWh to export.

## Import Limit

Maximum power that can be imported from the grid (kW).

**Optional** - if not specified, import is unlimited.

Use this to model:

- Main breaker capacity (e.g., 60A × 240V ÷ 1000 = 14.4 kW)
- Grid connection agreement limits
- Distribution network constraints
- Regulatory import restrictions

**Example**: `15` for 15 kW maximum import

## Export Limit

Maximum power that can be exported to the grid (kW).

**Optional** - if not specified, export is unlimited.

Use this to model:

- Inverter export capacity
- Grid connection agreement limits
- Feed-in tariff restrictions
- Regulatory export caps (zero-export requirements, etc.)

**Example**: `10` for 10 kW maximum export

**Zero export**: Set to `0` to prevent any grid export (self-consumption only mode)

## Configuration Examples

### Dynamic Pricing with Forecasts

Use multiple sensors for time-varying pricing:

| Field            | Value                                                               |
| ---------------- | ------------------------------------------------------------------- |
| **Name**         | Main Grid                                                           |
| **Import Price** | sensor.electricity_import_today, sensor.electricity_import_tomorrow |
| **Export Price** | sensor.electricity_export_today, sensor.electricity_export_tomorrow |
| **Import Limit** | 15                                                                  |
| **Export Limit** | 10                                                                  |

### Fixed Pricing

Use single sensor or input_number for constant pricing:

| Field            | Value                           |
| ---------------- | ------------------------------- |
| **Name**         | Grid Connection                 |
| **Import Price** | input_number.fixed_import_price |
| **Export Price** | input_number.fixed_export_price |
| **Import Limit** | 20                              |
| **Export Limit** | 5                               |

For more examples and sensor creation, see the [Forecasts and Sensors guide](../forecasts-and-sensors.md).

## Sensors Created

These sensors provide real-time visibility into grid interactions and costs.

| Sensor                         | Unit   | Description                                                |
| ------------------------------ | ------ | ---------------------------------------------------------- |
| `sensor.{name}_power_imported` | kW     | Optimal power imported from grid (always positive or zero) |
| `sensor.{name}_power_exported` | kW     | Optimal power exported to grid (always positive or zero)   |
| `sensor.{name}_price_import`   | \$/kWh | Current import price                                       |
| `sensor.{name}_price_export`   | \$/kWh | Current export price                                       |

All sensors include a `forecast` attribute containing future optimized values for upcoming periods.

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
