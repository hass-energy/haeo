# Grid Configuration

The grid entity represents your connection to the electricity network.
It allows bidirectional power flow: importing (buying) electricity and exporting (selling) electricity.

## Overview

A grid in HAEO represents:

- **Import capability**: Buying electricity from the grid
- **Export capability**: Selling electricity to the grid
- **Pricing**: Cost to import, revenue from export (via forecasts)
- **Power limits**: Optional maximum import/export rates

## Configuration Fields

| Field            | Type               | Required | Default | Description                                              |
| ---------------- | ------------------ | -------- | ------- | -------------------------------------------------------- |
| **Name**         | String             | Yes      | -       | Unique identifier (e.g., "Main Grid", "Grid Connection") |
| **Import Price** | Forecast sensor(s) | Yes      | -       | Price per kWh for importing electricity                  |
| **Export Price** | Forecast sensor(s) | Yes      | -       | Revenue per kWh for exporting electricity                |
| **Import Limit** | Number (kW)        | No       | -       | Maximum import power                                     |
| **Export Limit** | Number (kW)        | No       | -       | Maximum export power                                     |

### Name

Use descriptive, user-friendly names without special characters:

- ✅ "Main Grid", "Grid Connection", "House Meter"
- ❌ "Main_Grid", "grid1", "grd"

### Import Price

**Forecast sensor(s)** providing electricity import prices over time.

- **Format**: Single sensor or list of sensors
- **Unit**: \$/kWh
- **Required**: Yes

**Single forecast sensor**:

```yaml
Import Price: sensor.electricity_import_price
```

**Multiple forecast sensors** (e.g., today + tomorrow):

```yaml
Import Price:
  - sensor.electricity_import_price_today
  - sensor.electricity_import_price_tomorrow
```

HAEO automatically merges multiple forecasts into a continuous timeline.

!!! info "Forecast Sensors Required"

    Grid pricing **must** be provided via forecast sensors.
    Even for fixed pricing, create a forecast sensor that returns a constant value.

    See [Forecasts & Sensors](../forecasts-and-sensors.md) for examples of creating constant-price forecast sensors and time-of-use tariff sensors.

### Export Price

**Forecast sensor(s)** providing electricity export revenue over time.

- **Format**: Single sensor or list of sensors
- **Unit**: \$/kWh
- **Required**: Yes

Same configuration options as import price.

!!! info "Export vs Import Pricing"

    Typically, export prices are lower than import prices:

    - **Import**: \$0.25/kWh (what you pay)
    - **Export**: \$0.10/kWh (what you receive)

    This price difference incentivizes self-consumption and strategic battery usage.

!!! note "Export Prices as Negative Costs"

    Export prices are automatically treated as negative costs in optimization.
    Enter positive values (e.g., 0.10) and HAEO converts them to revenue.
    The optimizer maximizes profit from selling electricity at these prices.

!!! warning "Export Price Must Be Less Than Import Price"

    If export price equals or exceeds import price, the optimizer will find arbitrage opportunities.
    It will charge batteries from the grid and immediately export, creating infinite profit loops.
    Always ensure import price > export price to match real-world utility economics.

### Import Limit

Maximum power that can be imported from the grid (kW).

- **Optional** - if not specified, import is unlimited.

Use this to model:

- Main breaker capacity

- Grid connection limits

- Fuse ratings

- **Example**: `10` for 10 kW maximum import

### Export Limit

Maximum power that can be exported to the grid (kW).

- **Optional** - if not specified, export is unlimited.

Use this to model:

- Inverter export limits

- Grid connection agreements

- Feed-in tariff restrictions

- **Example**: `5` for 5 kW maximum export

!!! warning "Regulatory Limits"

    Some jurisdictions limit export to a percentage of import capacity, or prohibit export entirely.
    Configure accordingly.

## Configuration Examples

### Dynamic pricing with forecast sensors

| Field            | Value                                                     |
| ---------------- | --------------------------------------------------------- |
| **Name**         | Main Grid                                                 |
| **Import Price** | sensor.amber_general_price, sensor.amber_forecast_price   |
| **Export Price** | sensor.amber_feed_in_price, sensor.amber_feed_in_forecast |
| **Import Limit** | 15 kW                                                     |
| **Export Limit** | 10 kW                                                     |

### Fixed pricing with template sensors

| Field            | Value                        |
| ---------------- | ---------------------------- |
| **Name**         | Grid Connection              |
| **Import Price** | sensor.constant_import_price |
| **Export Price** | sensor.constant_export_price |

See [Forecasts & Sensors](../forecasts-and-sensors.md) for creating constant-price and time-of-use template sensors.

## How HAEO Uses Grid Configuration

When you configure grid pricing through forecast sensors, HAEO optimizes over the forecast horizon to minimize total cost.
The optimizer charges batteries when prices are low, discharges when prices are high, and adjusts export based on export price forecasts.

The grid can import or export, but not simultaneously:

- Positive power = importing from grid
- Negative power = exporting to grid

## Sensors Created

HAEO creates this sensor for each grid:

| Sensor                | Description                                                         |
| --------------------- | ------------------------------------------------------------------- |
| `sensor.{name}_power` | Optimal grid power (kW). Positive = importing, negative = exporting |

The sensor includes forecast attributes with future timestamped values.

## Troubleshooting

### Grid Always Importing

If your system always imports and never uses battery/solar:

1. **Check price forecasts**: Ensure forecasts are working (see [forecasts troubleshooting](../forecasts-and-sensors.md#troubleshooting-forecasts))
2. **Verify pricing**: Ensure import price > export price
3. **Review connections**: Grid must be connected to other entities
4. **Check battery SOC**: Battery may be at minimum SOC

### Grid Always Exporting

If your system exports even when import would be cheaper:

1. **Check export limits**: May be forcing export
2. **Verify pricing**: Ensure export price < import price
3. **Review load configuration**: May have load misconfigured

### Price Forecasts Not Working

If HAEO isn't responding to price changes:

1. **Check forecast format**: See [forecast requirements](../forecasts-and-sensors.md#forecast-attribute-format)
2. **Verify timestamps**: Must be ISO format with timezone
3. **Check sensor updates**: Ensure forecasts update regularly
4. **Review horizon**: Forecasts must cover the optimization horizon

See the [troubleshooting guide](../troubleshooting.md) for more solutions.

## Related Documentation

- [Forecasts & Sensors](../forecasts-and-sensors.md) - Creating price forecast sensors
- [Battery Configuration](battery.md) - Batteries work with grid pricing
- [Connections](connections.md) - Connect grid to your network
- [Grid Modeling](../../modeling/grid.md) - Mathematical formulation
- [Troubleshooting](../troubleshooting.md) - Common issues

## Next Steps

Extend your grid setup with these follow-up guides.

<div class="grid cards" markdown>

- :material-battery:{ .lg .middle } __Add a battery__

    Store inexpensive energy for later use while respecting device constraints.

    [:material-arrow-right: Battery guide](battery.md)

- :material-weather-sunny:{ .lg .middle } __Add solar generation__

    Bring photovoltaic production into the network for self-consumption or export.

    [:material-arrow-right: Photovoltaics guide](photovoltaics.md)

- :material-source-branch:{ .lg .middle } __Define connections__

    Configure energy flow paths between the grid and other elements.

    [:material-arrow-right: Connection setup](connections.md)

- :material-chart-line:{ .lg .middle } __View optimization results__

    Confirm the power flows HAEO produces with your updated configuration.

    [:material-arrow-right: Optimization overview](../optimization.md)

</div>
