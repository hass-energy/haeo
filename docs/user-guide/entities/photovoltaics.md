# Photovoltaics Configuration

Solar panels that generate electricity. HAEO optimizes how generated power is used, with optional curtailment.

## Configuration Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| **Name** | String | Yes | - | Unique identifier |
| **Forecast** | Sensor(s) | Yes | - | Solar generation forecast |
| **Production Price** | Number (\$/kWh) | No | 0 | Value per kWh generated |
| **Curtailment** | Boolean | No | false | Allow reducing generation |

### Name

Descriptive identifier: "Rooftop Solar", "East Array", "Ground Mount"

### Forecast

Forecast sensor(s) providing solar power predictions (kW).

Single sensor:
```yaml
Forecast: sensor.solcast_pv_forecast
```

Multiple sensors (merged):
```yaml
Forecast:
  - sensor.solar_forecast_today
  - sensor.solar_forecast_tomorrow
```

**Integrations**: Solcast, Open-Meteo Solar Forecast, Forecast.Solar

### Production Price

Price per kWh generated. Usually 0 (solar is free). Positive value models feed-in tariff.

### Curtailment

Allow reducing generation below forecast.

**When enabled**: HAEO can curtail if export prices are negative or export limit reached.

**Requirement**: Inverter must support active power limiting.

**Default**: Disabled (generation follows forecast exactly).

## Configuration Example

```yaml
Name: Rooftop Solar
Forecast: sensor.solcast_pv_forecast
Production Price: 0
Curtailment: false  # Standard operation
```

## Sensors Created

| Sensor | Unit | Description |
|--------|------|-------------|
| `{name}_power` | kW | Current/forecast generation |

**Forecast attribute**: Future generation values with timestamps.

## Troubleshooting

**No generation shown**: Check forecast sensor exists, has data, uses kW units, covers current time.

**Curtailment not working**: Verify curtailment enabled, export prices actually negative, inverter supports it.

**Incorrect forecast**: Verify sensor in HA developer tools, check units (kW not kWh), confirm system size matches.

## Multiple Arrays

Configure separate photovoltaics entities for different orientations/locations:

```yaml
# East-facing
Name: East Panels
Forecast: sensor.solar_forecast_east

# West-facing  
Name: West Panels
Forecast: sensor.solar_forecast_west
```

Better daily coverage vs single orientation.

## Related Documentation

- [Photovoltaics Modeling](../../modeling/photovoltaics.md)
- [Grid Configuration](grid.md)
- [Battery Configuration](battery.md)
- [Forecasts Guide](../forecasts-and-sensors.md)

[:octicons-arrow-right-24: Continue to Load Configuration](loads.md)
