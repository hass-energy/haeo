# Load Configuration

Loads represent electricity consumption. Two types: constant (fixed power) and forecast (time-varying).

## Load Types

| Type | Configuration | Best For |
|------|--------------|----------|
| Constant Load | Fixed power value | Baseline, always-on devices |
| Forecast Load | Forecast sensor(s) | Variable loads, HVAC, scheduled |

## Configuration Fields

### Constant Load

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| **Name** | String | Yes | - | Unique identifier |
| **Type** | "Constant Load" | Yes | - | Load type |
| **Power** | Number (kW) | Yes | - | Fixed consumption |

### Forecast Load

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| **Name** | String | Yes | - | Unique identifier |
| **Type** | "Forecast Load" | Yes | - | Load type |
| **Forecast** | Sensor(s) | Yes | - | Power consumption forecast |

## Name

Descriptive: "Base Load", "House Load", "HVAC Load", "EV Charger"

## Power (Constant Load)

Fixed consumption in kW.

**Determine value**: Measure overnight minimum, add always-on devices, add 10-20% margin.

**Typical values**:
- Small apartment: 0.2-0.4 kW
- Average home: 0.5-1.2 kW
- Large home: 1.0-2.0 kW

## Forecast (Forecast Load)

Forecast sensor(s) providing consumption predictions (kW).

Single or multiple sensors (merged):
```yaml
Forecast: sensor.house_load_forecast
# OR
Forecast:
  - sensor.load_forecast_today
  - sensor.load_forecast_tomorrow
```

**Creating forecasts**: Use statistics integration, template sensors, or ML models based on historical data.

## Configuration Examples

### Baseline Only

```yaml
Name: House Load
Type: Constant Load
Power: 2.5  # kW
```

### Baseline + Variable (Recommended)

```yaml
# Constant baseline
Name: Base Load
Type: Constant Load
Power: 1.0

# Variable on top
Name: Variable Load
Type: Forecast Load
Forecast: sensor.variable_consumption
```

Total = 1.0 kW + forecast.

## Sensors Created

| Sensor | Unit | Description |
|--------|------|-------------|
| `{name}_power` | kW | Current load |

Load sensors reflect configured load (constant or forecast).

## Troubleshooting

**Optimization infeasible**: Load may exceed max supply (grid limit + solar + battery). Increase grid import limit or reduce load estimate.

**Forecast inaccurate**: Check forecast sensor in HA, verify units (kW not kWh), review historical accuracy, tune forecast model.

**Battery not discharging during peak**: Load may be too small, price differential insufficient, or battery degradation costs too high.

## Multiple Loads

Configure separate loads for different sources:

```yaml
# Baseline
Name: Baseline
Type: Constant Load
Power: 0.8

# HVAC
Name: HVAC
Type: Forecast Load
Forecast: sensor.hvac_forecast

# EV
Name: EV Charger
Type: Forecast Load
Forecast: sensor.ev_schedule
```

Total load = sum of all at net entity.

## Related Documentation

- [Load Modeling](../../modeling/loads.md)
- [Battery Configuration](battery.md)
- [Grid Configuration](grid.md)
- [Forecasts Guide](../forecasts-and-sensors.md)

[:octicons-arrow-right-24: Continue to Net Entity Configuration](net.md)
