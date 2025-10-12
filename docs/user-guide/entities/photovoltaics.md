# Photovoltaics Configuration

Photovoltaics (solar panels) generate electricity from sunlight. HAEO optimizes how this generated power is used.

## Configuration Fields

### Required Fields

#### Name

Unique identifier for the solar system.

**Example**: `Rooftop_Solar`, `East_Array`

#### Forecast

Sensor entity IDs providing solar power generation forecasts.

- **Format**: Single sensor or list of sensors
- **Unit**: kW
- **Example**: `sensor.solcast_forecast_today`

Supported integrations:

- [Open-Meteo Solar Forecast](https://github.com/rany2/ha-open-meteo-solar-forecast)
- Solcast Solar

### Optional Fields

#### Production Price

Value per kWh of solar generation (for feed-in tariffs).

**Default**: 0 \$/kWh

#### Curtailment

Whether solar output can be reduced (curtailed).

**Default**: false

Set to true if your inverter supports curtailment control.

## Example Configuration

```yaml
Name: Rooftop_Solar
Forecast:
  - sensor.solar_forecast_today
  - sensor.solar_forecast_tomorrow
Production Price: 0.05 $/kWh
Curtailment: false
```

## Related Documentation

- [Photovoltaics Modeling](../../modeling/photovoltaics.md)
- [Grid Configuration](grid.md)
- [Connections](../connections.md)

[:octicons-arrow-right-24: Continue to Load Configuration](loads.md)
