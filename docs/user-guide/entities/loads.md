# Load Configuration

Loads represent electricity consumption in your system. HAEO supports two types: constant loads (fixed power) and forecast loads (variable power).

## Constant Load

Fixed power consumption that doesn't change.

### Configuration Fields

#### Name
Unique identifier.

#### Power
Constant power consumption in kW.

**Example**: `2.5` for 2.5 kW base load

### Example

```yaml
Name: Base_Load
Type: Constant Load
Power: 1.5 kW
```

## Forecast Load

Variable consumption with forecast data.

### Configuration Fields

#### Name
Unique identifier.

#### Forecast
Sensor entity IDs providing power consumption forecasts.

**Format**: Single sensor or list of sensors  
**Unit**: kW

### Example

```yaml
Name: House_Load
Type: Forecast Load
Forecast:
  - sensor.load_forecast_today
  - sensor.load_forecast_tomorrow
```

## Related Documentation

- [Load Modeling](../../modeling/loads.md)
- [Connections](../connections.md)

[:octicons-arrow-right-24: Continue to Net Entity Configuration](net.md)
