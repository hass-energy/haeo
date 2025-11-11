# Load Configuration

Loads represent power consumption in your system.
The Load element uses forecast data to model any type of consumption pattern from fixed baseline loads to variable time-varying consumption.

## Configuration Fields

| Field        | Type                                     | Required | Default | Description                      |
| ------------ | ---------------------------------------- | -------- | ------- | -------------------------------- |
| **Name**     | String                                   | Yes      | -       | Unique identifier                |
| **Type**     | "Load"                                   | Yes      | -       | Element type                     |
| **Forecast** | [sensor(s)](../forecasts-and-sensors.md) | Yes      | -       | Power consumption sensor(s) (kW) |

## Forecast

Specify one or more Home Assistant sensor entities providing power consumption data.
The Load element is flexible and works with both constant and time-varying patterns.

### Single Sensor

```yaml
Forecast: sensor.house_load_forecast
```

HAEO reads the sensor's current value and any forecast data.
If the sensor only provides a current value, HAEO repeats it across the optimization horizon creating a constant load pattern.
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

## Constant Load Pattern

For fixed baseline consumption that doesn't vary over time, use an `input_number` helper providing a constant value.

### Creating a Constant Load

1. **Create Input Number Helper**:
   - Go to Settings → Devices & Services → Helpers
   - Add a new "Number" helper
   - Set name: "Base Load Power"
   - Set unit: kW
   - Set desired constant value (e.g., 1.0)

2. **Configure Load Element**:
   ```yaml
   Name: Base Load
   Type: Load
   Forecast: input_number.base_load_power
   ```

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

```yaml
Name: House Load
Type: Load
Forecast: sensor.house_load_forecast
```

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

```yaml
# Configuration 1: Constant baseline
Name: Base Load
Type: Load
Forecast: input_number.base_load_power  # Set to 1.0 kW
```

```yaml
# Configuration 2: Variable consumption on top
Name: Variable Load
Type: Load
Forecast: sensor.variable_consumption
```

Total consumption = 1.0 kW (constant) + variable forecast.

This approach:

- Simplifies forecast creation (only forecast variable portion)
- Ensures baseline is always covered
- Improves optimization reliability
- Makes it easier to adjust baseline without changing forecasts

## Multiple Sensors

Combine multiple load sources in a single element:

```yaml
Name: Total House Load
Type: Load
Forecast:
  - input_number.base_load        # 1.0 kW constant
  - sensor.ev_charger_schedule    # Variable
  - sensor.pool_pump_schedule     # Variable
  - sensor.hvac_forecast          # Variable
```

HAEO automatically sums all sensors at each timestamp, allowing you to model complex load profiles from simple components.

## Configuration Examples

### Simple Constant Load

```yaml
Name: Base Load
Type: Load
Forecast: input_number.constant_power  # 1.0 kW
```

### Variable Household Consumption

```yaml
Name: House Load
Type: Load
Forecast: sensor.house_consumption_forecast
```

### Combined Constant and Variable

```yaml
Name: Total Load
Type: Load
Forecast:
  - input_number.baseline_power   # 0.8 kW constant
  - sensor.appliance_forecast     # Variable on top
```

### Multiple Variable Sources

```yaml
Name: All Loads
Type: Load
Forecast:
  - sensor.base_consumption
  - sensor.ev_charger
  - sensor.pool_pump_schedule
  - sensor.hvac_system
```

## Sensors Created

| Sensor                | Unit | Description               |
| --------------------- | ---- | ------------------------- |
| `sensor.{name}_power` | kW   | Current period load power |

After optimization completes, the sensor shows the load value for the current optimization period.
The `forecast` attribute contains future load values for upcoming periods.

For constant loads, the sensor shows the same value for all periods.
For variable loads, the sensor reflects the forecast values for each period.

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

## Related Documentation

- [Forecasts and Sensors](../forecasts-and-sensors.md) - Understanding sensor data loading
- [Configuration Guide](../configuration.md) - Adding elements to your network
- [Battery Configuration](battery.md) - Pairing loads with storage
- [Grid Configuration](grid.md) - Grid import/export with loads
