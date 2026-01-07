# Grid

The grid represents your connection to the electricity network.
It allows bidirectional power flow: importing (buying) and exporting (selling) electricity.

!!! note "Connection endpoints"

    Grid elements appear in connection selectors only when Advanced Mode is enabled on your hub.

## Configuration

Grid configuration uses a two-step flow (see [Configuration](../configuration.md#two-step-element-configuration) for details):

1. **Step 1**: Enter name, connection, and select entities for each field (or "Configurable Entity" to enter a constant value)
2. **Step 2**: Enter constant values for any fields where you selected "Configurable Entity"

| Field                             | Type   | Required | Default | Description                                                |
| --------------------------------- | ------ | -------- | ------- | ---------------------------------------------------------- |
| **[Name](#name)**                 | String | Yes      | -       | Unique identifier for this grid                            |
| **[Import Price](#import-price)** | Price  | Yes      | -       | Price per kWh for importing electricity from grid (\$/kWh) |
| **[Export Price](#export-price)** | Price  | Yes      | -       | Revenue per kWh for exporting electricity to grid (\$/kWh) |
| **[Import Limit](#import-limit)** | Power  | No       | -       | Maximum import power from grid                             |
| **[Export Limit](#export-limit)** | Power  | No       | -       | Maximum export power to grid                               |

## Name

Unique identifier for this grid within your HAEO configuration.
Used to create sensor entity IDs and identify the grid in connections.

**Examples**: "Main Grid", "Grid Connection", "Utility"

## Import Price

Configure the cost of importing electricity from the grid.
You can use either a constant value or one or more Home Assistant sensors.

**Constant value**: Enter a fixed price in \$/kWh that stays the same for all periods.
Use this for simple flat-rate tariffs.

**Entity Link**: Select one or more Home Assistant sensors providing electricity import pricing.
Use this for time-of-use rates or dynamic pricing.

**Sign convention**: Import prices should be positive numbers representing the cost you pay to buy electricity from the grid.
For example, `0.25` means you pay \$0.25 per kWh imported.

**Sensor examples**:

| Scenario                   | Sensors                                                           |
| -------------------------- | ----------------------------------------------------------------- |
| Single price sensor        | sensor.electricity_import_price                                   |
| Today + tomorrow forecasts | sensor.electricity_price_today, sensor.electricity_price_tomorrow |

When using sensors, provide all relevant price sensors (today, tomorrow, etc.) to ensure complete horizon coverage.
See the [Forecasts and Sensors guide](../forecasts-and-sensors.md) for details on how HAEO processes sensor data.

## Export Price

Configure the revenue for exporting electricity to the grid.
You can use either a constant value or one or more Home Assistant sensors.

**Constant value**: Enter a fixed price in \$/kWh.
Use this for simple feed-in tariffs.

**Entity Link**: Select one or more Home Assistant sensors providing export pricing.
Use this for dynamic feed-in rates.

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

**Optional**: Leave this field empty in step 1 to leave import unlimited.
You can also select "Configurable Entity" to enter a constant value, or link to sensors for dynamic limits.

Use this to model:

- Main breaker capacity (e.g., 60A × 240V ÷ 1000 = 14.4 kW)
- Grid connection agreement limits
- Distribution network constraints
- Regulatory import restrictions

**Example**: `15` for 15 kW maximum import

## Export Limit

Maximum power that can be exported to the grid (kW).

**Optional**: Leave this field empty in step 1 to leave export unlimited.
You can also select "Configurable Entity" to enter a constant value, or link to sensors for dynamic limits.

Use this to model:

- Inverter export capacity
- Grid connection agreement limits
- Feed-in tariff restrictions
- Regulatory export caps (zero-export requirements, etc.)

**Example**: `10` for 10 kW maximum export

**Zero export**: Set to `0` to prevent any grid export (self-consumption only mode)

## Configuration Examples

### Dynamic Pricing with Forecasts

Select multiple sensors for time-varying pricing:

| Field            | Value                                                               |
| ---------------- | ------------------------------------------------------------------- |
| **Name**         | Main Grid                                                           |
| **Import Price** | sensor.electricity_import_today, sensor.electricity_import_tomorrow |
| **Export Price** | sensor.electricity_export_today, sensor.electricity_export_tomorrow |
| **Import Limit** | 15                                                                  |
| **Export Limit** | 10                                                                  |

### Fixed Pricing

Select "Configurable Entity" for fixed rates, or link to an input_number for adjustable rates:

| Field            | Selection           | Value |
| ---------------- | ------------------- | ----- |
| **Name**         | -                   | Grid  |
| **Import Price** | Configurable Entity | 0.25  |
| **Export Price** | Configurable Entity | 0.08  |
| **Import Limit** | Configurable Entity | 20    |
| **Export Limit** | Configurable Entity | 5     |

For more examples and sensor configuration, see the [Forecasts and Sensors guide](../forecasts-and-sensors.md).

### Input Entities

Each configured field creates a corresponding input entity in Home Assistant.
Input entities appear as Number entities with the `config` entity category.

| Input                            | Unit   | Description                               |
| -------------------------------- | ------ | ----------------------------------------- |
| `number.{name}_import_price`     | \$/kWh | Import price from configured value/sensor |
| `number.{name}_export_price`     | \$/kWh | Export price from configured value/sensor |
| `number.{name}_max_import_power` | kW     | Maximum import power (if configured)      |
| `number.{name}_max_export_power` | kW     | Maximum export power (if configured)      |

Input entities are only created for fields you configure with "Configurable Entity".
If you leave an optional limit field empty, no input entity is created for that field.

Input entities include a `forecast` attribute showing values for each optimization period.
See the [Input Entities developer guide](../../developer-guide/inputs.md) for details on input entity behavior.

## Sensors Created

### Sensor Summary

A Grid element creates 1 device in Home Assistant with the following sensors.

| Sensor                                                                   | Unit  | Description                                 |
| ------------------------------------------------------------------------ | ----- | ------------------------------------------- |
| [`sensor.{name}_power_import`](#import-power)                            | kW    | Power imported from grid                    |
| [`sensor.{name}_power_export`](#export-power)                            | kW    | Power exported to grid                      |
| [`sensor.{name}_cost_import`](#import-cost)                              | \$    | Cost of importing electricity               |
| [`sensor.{name}_cost_export`](#export-cost)                              | \$    | Revenue from exporting electricity          |
| [`sensor.{name}_cost_net`](#net-cost)                                    | \$    | Net cost (import cost minus export revenue) |
| [`sensor.{name}_power_max_import`](#max-import-power)                    | kW    | Maximum import power (when limited)         |
| [`sensor.{name}_power_max_export`](#max-export-power)                    | kW    | Maximum export power (when limited)         |
| [`sensor.{name}_power_max_import_price`](#max-import-power-shadow-price) | \$/kW | Value of additional import capacity         |
| [`sensor.{name}_power_max_export_price`](#max-export-power-shadow-price) | \$/kW | Value of additional export capacity         |

The `power_max_*` sensors are only created when the corresponding limit is configured.
The `cost_*` sensors are only created when the corresponding price is configured.

### Import Power

The optimal power being imported from the grid at each time period.

Values are always positive or zero.
When importing, this represents electricity you're buying from the utility.
A value of 0 means no import is occurring (either self-sufficient or exporting).

**Example**: A value of 3.5 kW means the optimization determined that importing 3.5 kW from the grid at this time minimizes total system cost.

### Export Power

The optimal power being exported to the grid at each time period.

Values are always positive or zero.
When exporting, this represents electricity you're selling back to the utility.
A value of 0 means no export is occurring (either self-consuming all generation or importing).

**Example**: A value of 2.1 kW means the optimization determined that exporting 2.1 kW to the grid at this time maximizes total system value (typically during high export prices or excess generation).

### Import Cost

The cost of electricity imported from the grid at each time period.
Calculated as import price multiplied by import power multiplied by period duration.

Values are always positive or zero, representing money you pay to the utility.
Only created when an import price is configured.

**Example**: A value of \$0.50 means you're paying \$0.50 to import electricity during this time period.

### Export Cost

The revenue from electricity exported to the grid at each time period.
Calculated as export price multiplied by export power multiplied by period duration.

Values are always negative or zero, representing money you earn from the utility (revenue is shown as negative cost).
Only created when an export price is configured.

**Example**: A value of -\$0.30 means you're earning \$0.30 from exporting electricity during this time period.

### Net Cost

The net cost of grid usage at each time period.
Calculated as import cost plus export cost.

When both import and export prices are configured, this shows your net spending or earnings.
Positive values mean net spending; negative values mean net earnings.

**Example**: If you import \$0.50 worth and export \$0.30 worth in a period, the net cost is \$0.20 (net spending).

### Max Import Power

The configured maximum import power limit.
Only created when an import limit is configured.

Shows the power limit used in the optimization.

### Max Export Power

The configured maximum export power limit.
Only created when an export limit is configured.

Shows the power limit used in the optimization.

### Max Import Power Shadow Price

The marginal value of additional import capacity.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would decrease if the import limit were increased by 1 kW at this time period.

**Interpretation**:

- **Zero value**: Import limit is not constraining (you're importing below the limit or not importing at all)
- **Positive value**: Import limit is binding and constraining the optimization
    - The value represents how much system cost would decrease per kW of additional import capacity
    - Higher values indicate the import limit is causing significant cost increases
    - Suggests that more import capacity would be valuable at this time

**Example**: A value of 0.15 means that if you could import 1 kW more, the total system cost would decrease by \$0.15 at this time period.

### Max Export Power Shadow Price

The marginal value of additional export capacity.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price shows how much the total system cost would decrease if the export limit were increased by 1 kW at this time period.

**Interpretation**:

- **Zero value**: Export limit is not constraining (you're exporting below the limit or not exporting at all)
- **Positive value**: Export limit is binding and constraining the optimization
    - The value represents how much system cost would decrease per kW of additional export capacity
    - Higher values indicate the export limit is preventing valuable exports
    - Suggests that more export capacity would be valuable at this time

**Example**: A value of 0.08 means that if you could export 1 kW more, the total system cost would decrease by \$0.08 at this time period (you'd earn more revenue from exports).

---

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

    [:material-arrow-right: Grid modeling](../../modeling/device-layer/grid.md)

</div>
