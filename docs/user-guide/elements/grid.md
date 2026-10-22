# Grid

The grid represents your connection to the electricity network.
It allows bidirectional power flow: importing (buying) and exporting (selling) electricity.

## Configuration

Grid configuration uses a single-step flow where you enter the name and configure each input field.
For each field, select "Entity" to link to a sensor, "Constant" to enter a fixed value, or "None" for optional fields you don't need.

| Field                             | Type   | Required | Default | Description                                                |
| --------------------------------- | ------ | -------- | ------- | ---------------------------------------------------------- |
| **[Name](#name)**                 | String | Yes      | -       | Unique identifier for this grid                            |
| **[Import Price](#import-price)** | Price  | Yes      | -       | Price per kWh for importing electricity from grid (\$/kWh) |
| **[Export Price](#export-price)** | Price  | Yes      | -       | Revenue per kWh for exporting electricity to grid (\$/kWh) |
| **[Import Limit](#import-limit)** | Power  | No       | -       | Maximum import power from grid                             |
| **[Export Limit](#export-limit)** | Power  | No       | -       | Maximum export power to grid                               |

See [Where values are measured](../measurement-points.md) for the convention HAEO uses for where limits, prices, and reported power apply.

## Name

Unique identifier for this grid within your HAEO configuration.
Used to create sensor entity IDs and identify the grid in connections.

**Examples**: "Main Grid", "Grid Connection", "Utility"

## Import price

Configure the cost of importing electricity from the grid.
You can use either a constant value or one or more Home Assistant sensors.

**Constant**: Select "Constant" and enter a fixed price in \$/kWh directly.
Use this for simple flat-rate tariffs.

**Sensor link**: Select one or more Home Assistant sensors providing electricity import pricing.
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

## Export price

Configure the revenue for exporting electricity to the grid.
You can use either a constant value or one or more Home Assistant sensors.

**Constant**: Select "Constant" and enter a fixed price in \$/kWh directly.
Use this for simple feed-in tariffs.

**Sensor link**: Select one or more Home Assistant sensors providing export pricing.
Use this for dynamic feed-in rates.

**Sign convention**: Export prices should be positive numbers representing the revenue you receive for selling electricity to the grid.
For example, `0.10` means you receive \$0.10 per kWh exported.

**Typical relationship**: Export price is usually lower than import price.

- Import: \$0.25/kWh (what you pay to buy)
- Export: \$0.10/kWh (what you receive to sell)

This price difference incentivizes self-consumption and strategic battery usage.

**Negative export prices**: When the grid operator charges you to export use negative values.
For example, `-0.05` means you pay \$0.05 per kWh to export.

## Import limit

Maximum power that can be imported from the grid (kW).

**Optional**: Select "None" to leave import unlimited.
You can also select "Constant" to enter a fixed limit, or "Entity" to link to sensors for dynamic limits.

Use this to model:

- Main breaker capacity (e.g., 60A × 240V ÷ 1000 = 14.4 kW)
- Grid connection agreement limits
- Distribution network constraints
- Regulatory import restrictions

**Example**: `15` for 15 kW maximum import

## Export limit

Maximum power that can be exported to the grid (kW).

**Optional**: Select "None" to leave export unlimited.
You can also select "Constant" to enter a fixed limit, or "Entity" to link to sensors for dynamic limits.

Use this to model:

- Inverter export capacity
- Grid connection agreement limits
- Feed-in tariff restrictions
- Regulatory export caps (zero-export requirements, etc.)

**Example**: `10` for 10 kW maximum export

**Zero export**: Set to `0` to prevent any grid export (self-consumption only mode)

## Configuration examples

### Dynamic pricing with forecasts

Select multiple sensors for time-varying pricing:

| Field            | Value                                                               |
| ---------------- | ------------------------------------------------------------------- |
| **Name**         | Main Grid                                                           |
| **Import Price** | sensor.electricity_import_today, sensor.electricity_import_tomorrow |
| **Export Price** | sensor.electricity_export_today, sensor.electricity_export_tomorrow |
| **Import Limit** | 15                                                                  |
| **Export Limit** | 10                                                                  |

### Fixed pricing

Select "Constant" for fixed rates, or "Entity" to link to an input_number for adjustable rates:

| Field            | Selection | Value |
| ---------------- | --------- | ----- |
| **Name**         | -         | Grid  |
| **Import Price** | Constant  | 0.25  |
| **Export Price** | Constant  | 0.08  |
| **Import Limit** | Constant  | 20    |
| **Export Limit** | Constant  | 5     |

For more examples and sensor configuration, see the [Forecasts and Sensors guide](../forecasts-and-sensors.md).

### Input entities

Each field you configure creates an input entity on the grid's device.
Input entities appear as Number entities with the `config` entity category.
Their IDs combine the grid's name with the entity's name, so a grid named "Grid" has `number.grid_import_price`.

| Input                        | Unit   | Description                  |
| ---------------------------- | ------ | ---------------------------- |
| `number.{name}_import_price` | \$/kWh | Import price                 |
| `number.{name}_export_price` | \$/kWh | Export price                 |
| `number.{name}_import_limit` | kW     | Import limit (if configured) |
| `number.{name}_export_limit` | kW     | Export limit (if configured) |

A field set to "Constant" can be adjusted from its input entity at runtime.
A field linked to sensors shows the values HAEO reads from them.
If you set an optional field to "None", no input entity is created for it.

Input entities include a `forecast` attribute showing values for each optimization period.
See [How data updates work](../data-updates.md) for how input entities receive their values.

## Sensors created

### Sensor summary

A Grid element creates 1 device in Home Assistant with the following sensors.

| Sensor                                                                          | Unit   | Description                                 |
| ------------------------------------------------------------------------------- | ------ | ------------------------------------------- |
| [`sensor.{name}_import_power`](#import-power)                                   | kW     | Power imported from grid                    |
| [`sensor.{name}_export_power`](#export-power)                                   | kW     | Power exported to grid                      |
| [`sensor.{name}_active_power`](#active-power)                                   | kW     | Net grid power (import minus export)        |
| [`sensor.{name}_import_cost`](#import-cost)                                     | \$     | Cost of importing electricity               |
| [`sensor.{name}_export_revenue`](#export-revenue)                               | \$     | Revenue from exporting electricity          |
| [`sensor.{name}_net_cost`](#net-cost)                                           | \$     | Net cost (import cost minus export revenue) |
| [`sensor.{name}_max_import_power_shadow_price`](#max-import-power-shadow-price) | \$/kWh | Value of additional import capacity         |
| [`sensor.{name}_max_export_power_shadow_price`](#max-export-power-shadow-price) | \$/kWh | Value of additional export capacity         |

The shadow price sensors are only created when the corresponding limit is configured.

### Import power

The optimal power being imported from the grid at each time period.

Values are always positive or zero.
When importing, this represents electricity you're buying from the utility.
A value of 0 means no import is occurring (either self-sufficient or exporting).

**Example**: A value of 3.5 kW means the optimization determined that importing 3.5 kW from the grid at this time minimizes total system cost.

### Export power

The optimal power being exported to the grid at each time period.

Values are always positive or zero.
When exporting, this represents electricity you're selling back to the utility.
A value of 0 means no export is occurring (either self-consuming all generation or importing).

**Example**: A value of 2.1 kW means the optimization determined that exporting 2.1 kW to the grid at this time maximizes total system value (typically during high export prices or excess generation).

### Active power

The net power flowing through the grid connection at each time period.
Calculated as import power minus export power.

Positive values mean the site is importing; negative values mean it is exporting.

### Import cost

The cost of electricity imported from the grid over the forecast horizon.
Each period adds import price multiplied by import power multiplied by period duration.

The sensor state is the total for the whole horizon, and its `forecast` attribute shows the running total at each period.
Values are always positive or zero, representing money you pay to the utility.

**Example**: A value of \$4.50 means the plan spends \$4.50 on imports over the horizon.

### Export revenue

The revenue from electricity exported to the grid over the forecast horizon.
Each period adds export price multiplied by export power multiplied by period duration.

The sensor state is the total for the whole horizon, and its `forecast` attribute shows the running total at each period.
Values are positive when you earn money from exports, and negative when negative export prices mean you pay to export.

**Example**: A value of \$1.30 means the plan earns \$1.30 from exports over the horizon.

### Net cost

The net cost of grid usage over the forecast horizon.
Calculated as import cost minus export revenue.

Positive values mean net spending; negative values mean net earnings.

**Example**: If the plan imports \$4.50 worth and exports \$1.30 worth, the net cost is \$3.20 (net spending).

### Max import power shadow price

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

### Max export power shadow price

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

### Sensor not found

**Problem**: Error "Input … has no reading from …", or an input entity shows as unavailable

**Solutions**:

- Verify sensor entity IDs exist in Home Assistant
- Check sensors are available (not "unavailable" or "unknown")
- Ensure pricing integration is configured correctly
- Verify sensors have appropriate device class (e.g., `monetary` for prices)

### Incorrect price values

**Problem**: Price values don't match expectations

**Check**:

- Sensor units match HAEO expectations (uses Home Assistant's native currency units)
- Multiple sensors sum correctly (intended?)
- Forecast data quality from source
- Import price > export price (prevents arbitrage)

### Grid not optimizing

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

## Next steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connect to network**

    ---

    Learn how to connect your grid to other elements using connections.

    [:material-arrow-right: Connections guide](connection.md)

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
