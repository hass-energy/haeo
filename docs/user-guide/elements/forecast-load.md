# Forecast Load Configuration

Forecast loads represent time-varying power consumption based on sensor data.
Use this element for variable household consumption, scheduled devices, or HVAC systems.

## Configuration Fields

| Field        | Type                                     | Required | Default | Description                      |
| ------------ | ---------------------------------------- | -------- | ------- | -------------------------------- |
| **Name**     | String                                   | Yes      | -       | Unique identifier                |
| **Type**     | "Forecast Load"                          | Yes      | -       | Element type                     |
| **Forecast** | [sensor(s)](../forecasts-and-sensors.md) | Yes      | -       | Power consumption sensor(s) (kW) |

## Forecast

Specify one or more Home Assistant sensor entities providing power consumption data.

### Single Sensor

```yaml
Forecast: sensor.house_load_forecast
```

HAEO reads the sensor's current value and any forecast data.
If the sensor only provides a current value, HAEO repeats it across the optimization horizon.
If the sensor includes forecast data, HAEO interpolates between forecast points for each optimization period.

### Multiple Sensors

Provide multiple sensors to combine different load sources:

```yaml
Forecast:
  - sensor.base_load
  - sensor.ev_charger_schedule
  - sensor.hvac_forecast
```

HAEO combines multiple sensors by:

- Summing present values together
- Merging forecast series on shared timestamps
- Adding values at each timestamp

This makes it easy to model separate load components without manual addition.

### How It Works

See the [Forecasts and Sensors guide](../forecasts-and-sensors.md) for complete details on:

- How HAEO extracts present values and forecasts
- Interpolation between forecast points
- Combining multiple sensors
- Forecast cycling when coverage is partial

## Configuration Example

```yaml
Name: House Load
Type: Forecast Load
Forecast: sensor.house_load_forecast
```

Multiple sensors:

```yaml
Name: Total House Load
Type: Forecast Load
Forecast:
  - sensor.base_consumption
  - sensor.ev_charger
  - sensor.pool_pump_schedule
```

## Sensors Created

| Sensor                | Unit | Description               |
| --------------------- | ---- | ------------------------- |
| `sensor.{name}_power` | kW   | Current period load power |

After optimization completes, the sensor shows the load value for the current optimization period.
The `forecast` attribute contains future load values for upcoming periods.

## Troubleshooting

### Sensor Not Found

**Problem**: Error "Sensors not found or unavailable"

**Solutions**:

- Verify sensor entity ID exists in Home Assistant
- Check sensor is available (not "unavailable" or "unknown")
- Ensure sensor provides numeric values

### Incorrect Load Values

**Problem**: Load values don't match expectations

**Check**:

- Sensor units are kW (not W or kWh)
- Multiple sensors sum correctly (intended?)
- Forecast data quality from source
- Current sensor reading is realistic

### Optimization Issues

**Problem**: Solver cannot find solution with forecast load

**Possible causes**:

- Load peaks exceed available supply capacity
- Grid import limits too low for peak loads
- Load not connected to power sources

**Solutions**:

- Increase grid import limit
- Verify connections from grid/battery to load
- Review forecast values for unrealistic peaks

## Related Documentation

- [Constant Load Configuration](constant-load.md) - Fixed consumption alternative
- [Forecasts and Sensors Guide](../forecasts-and-sensors.md) - Creating forecast sensors
- [Connections](connections.md) - Connecting loads to the network

## Next Steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connect to network**

    ---

    Learn how to connect your forecast load to power sources using connections.

    [:material-arrow-right: Connections guide](connections.md)

- :material-chart-line:{ .lg .middle } **Understand sensor loading**

    ---

    Deep dive into how HAEO uses forecast data for load predictions.

    [:material-arrow-right: Forecasts and sensors](../forecasts-and-sensors.md)

- :material-lightning-bolt:{ .lg .middle } **Add constant baseline**

    ---

    Combine forecast load with constant load for accurate total consumption.

    [:material-arrow-right: Constant load configuration](constant-load.md)

</div>
