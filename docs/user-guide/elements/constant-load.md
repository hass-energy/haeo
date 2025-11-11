# Constant Load

Constant loads represent fixed power consumption that doesn't vary over time.
Use this for baseline consumption from always-on devices.

## Configuration Fields

| Field     | Type            | Required | Default | Description             |
| --------- | --------------- | -------- | ------- | ----------------------- |
| **Name**  | String          | Yes      | -       | Unique identifier       |
| **Type**  | "Constant Load" | Yes      | -       | Element type            |
| **Power** | Number (kW)     | Yes      | -       | Fixed consumption power |

## Name

Use descriptive names that indicate the load's purpose:

- ✅ "Base Load", "Always On", "Background Consumption"
- ❌ "Load1", "Thing", "Device"

## Power

Fixed consumption in kilowatts (kW).
This power is assumed to be consumed constantly throughout the optimization horizon.

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

## Configuration Example

```yaml
Name: Base Load
Type: Constant Load
Power: 1.0  # kW
```

This configuration represents 1 kW of continuous consumption (24 kWh per day).

## Combined with Forecast Load

For most accurate optimization, use both constant and forecast loads:

```yaml
# Constant baseline
Name: Base Load
Type: Constant Load
Power: 1.0
```

```yaml
# Variable consumption on top
Name: Variable Load
Type: Forecast Load
Forecast: sensor.variable_consumption
```

Total consumption = 1.0 kW (constant) + variable forecast.

This approach:

- Simplifies forecast creation (only forecast variable portion)
- Ensures baseline is always covered
- Improves optimization reliability

## Sensors Created

### Power Sensor

**Entity ID**: `sensor.{name}_power`

**Unit**: kW

**Description**: Current optimal power consumption (always equals configured power value)

The power sensor for a constant load shows the fixed configured value at all timesteps.

## Troubleshooting

### Optimization Infeasible

If optimization fails with constant loads:

1. **Check total load vs supply**: Ensure grid + solar + battery can supply the constant load
2. **Verify power value**: Confirm the power value is in kW (not W or kWh)
3. **Review grid limits**: Grid import limit must be sufficient
4. **Check connections**: Load must be connected to the network

### Load Too High

If your constant load causes issues:

1. **Re-measure baseline**: Verify your baseline measurement is accurate
2. **Split into components**: Consider using forecast load for variable portions
3. **Review device list**: Ensure you haven't over-counted consumption

## When to Use Constant Load

Use constant loads for:

- ✅ Baseline consumption (always-on devices)
- ✅ Continuous industrial processes
- ✅ Known fixed loads (server rooms, refrigeration)
- ✅ Simplifying initial configuration

Avoid for:

- ❌ Variable household consumption (use forecast load)
- ❌ Scheduled devices (use forecast load)
- ❌ Time-of-day varying loads (use forecast load)

## Related Documentation

- [Forecast Load Configuration](forecast-load.md) - For variable consumption
- [Forecasts & Sensors Guide](../forecasts-and-sensors.md) - Creating forecast sensors
- [Load Modeling](../../modeling/loads.md) - Mathematical model
- [Connections](connections.md) - Connecting loads to the network

## Next Steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connect to network**

    ---

    Learn how to connect your constant load to power sources using connections.

    [:material-arrow-right: Connections guide](connections.md)

- :material-chart-line:{ .lg .middle } **Add variable consumption**

    ---

    Combine with forecast load to model both baseline and variable usage.

    [:material-arrow-right: Forecast load configuration](forecast-load.md)

- :material-home-lightning-bolt:{ .lg .middle } **Optimize power flow**

    ---

    Configure grid and battery elements to supply your loads efficiently.

    [:material-arrow-right: Grid configuration](grid.md)

</div>
