# Photovoltaics Configuration

Solar panels that generate electricity.
HAEO optimizes how generated power flows through your energy network.

## Configuration Fields

| Field                | Type                                     | Required | Default | Description                     |
| -------------------- | ---------------------------------------- | -------- | ------- | ------------------------------- |
| **Name**             | String                                   | Yes      | -       | Unique identifier               |
| **Forecast**         | [sensor(s)](../forecasts-and-sensors.md) | Yes      | -       | Solar generation sensor(s) (kW) |
| **Production Price** | Number (\$/kWh)                          | No       | 0       | Value per kWh generated         |
| **Curtailment**      | Boolean                                  | No       | false   | Allow reducing generation       |

## Forecast

Specify one or more Home Assistant sensors providing solar generation data.

### Single Sensor

```yaml
Forecast: sensor.solcast_pv_forecast
```

HAEO reads the sensor's current value and any forecast data.
For solar forecasts, this typically means predicted generation based on weather conditions.

### Multiple Sensors

Combine multiple solar arrays or forecast sources:

```yaml
Forecast:
  - sensor.solar_east_forecast
  - sensor.solar_west_forecast
```

HAEO combines multiple sensors by summing their values at each timestamp.
This is useful for:

- Multiple physical arrays (different orientations or locations)
- Multiple forecast providers for redundancy
- Separate tracking for different systems

See the [Forecasts and Sensors guide](../forecasts-and-sensors.md) for complete details on:

- How HAEO extracts present values and forecasts
- Interpolation between forecast points
- Combining multiple sensors
- Forecast cycling when coverage is partial

## Production Price

Cost or value per kWh of electricity generated.

**Default**: Leave empty for zero cost (most common case)

**When to use non-zero values**:

- Modeling opportunity cost of generation
- Accounting for maintenance costs per kWh
- Rare specialized scenarios

**Note**: Production price is NOT the same as export price.
Export revenue is configured on the Grid element.

## Curtailment

Allow HAEO to reduce generation below the forecast level.

**Default**: Disabled (generation follows forecast exactly)

**When enabled**: HAEO can curtail generation if:

- Export prices are negative (paying to export)
- Export limit is reached
- Battery is full and loads are satisfied

**Requirements**:

- Inverter must support active power limiting
- Control mechanism must be implemented separately (HAEO only optimizes)

## Configuration Example

Basic configuration:

```yaml
Name: Rooftop Solar
Forecast: sensor.solcast_pv_forecast
Production Price: 0
Curtailment: false
```

Multiple arrays:

```yaml
Name: Combined Solar
Forecast:
  - sensor.east_array_forecast
  - sensor.west_array_forecast
Production Price: 0
Curtailment: false
```

## Sensors Created

| Sensor                | Unit | Description               |
| --------------------- | ---- | ------------------------- |
| `sensor.{name}_power` | kW   | Current period generation |

After optimization completes, the sensor shows the generation value for the current optimization period.
The `forecast` attribute contains future generation values for upcoming periods.

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

## Related Documentation

- [Forecasts and Sensors Guide](../forecasts-and-sensors.md) - Understanding sensor data loading
- [Connections](connections.md) - Connecting photovoltaics to the network
- [Grid Configuration](grid.md) - Exporting solar generation
- [Battery Configuration](battery.md) - Storing solar generation

## Next Steps

<div class="grid cards" markdown>

- :material-solar-power:{ .lg .middle } **Connect to network**

    ---

    Learn how to connect your photovoltaics to other elements using connections.

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
