# Load Modeling

HAEO supports two load types: constant (fixed power) and forecast (time-varying power).

## Constant Load

### Decision Variables

None - constant parameter.

### Parameters

- $P_{\text{constant}}$: Fixed power consumption (kW) - from `power` config

### Constraints

$$
P_{\text{load}}(t) = P_{\text{constant}} \quad \forall t
$$

Load power is fixed at all time steps.

### Physical Interpretation

Represents baseline consumption: refrigerators, network equipment, standby power, always-on devices.

## Forecast Load

### Decision Variables

None - follows forecast parameter.

### Parameters

- $P_{\text{forecast}}(t)$: Forecasted power at time $t$ (kW) - from `forecast` sensors

### Constraints

$$
P_{\text{load}}(t) = P_{\text{forecast}}(t) \quad \forall t
$$

Load follows forecast exactly.

### Physical Interpretation

Represents time-varying consumption: HVAC, cooking, EV charging, occupancy-based loads.

Forecast accuracy directly impacts optimization quality.

## Combined Usage

Typical systems use both:

- **Constant load**: Baseline (0.5-2 kW)
- **Forecast load**: Variable consumption (time-dependent)

Total load at net entity = sum of all connected loads.

## Configuration Impact

| Load Type | Accuracy Needed | Best For                           |
| --------- | --------------- | ---------------------------------- |
| Constant  | Rough estimate  | Simple setup, stable consumption   |
| Forecast  | High accuracy   | Variable loads, optimization value |

**Overestimating load**: May cause infeasibility if supply can't meet.

**Underestimating load**: Real system may import more than optimized.

## Related Documentation

- [Load Configuration](../user-guide/elements/constant-load.md)
- [Forecast Load Configuration](../user-guide/elements/forecast-load.md)
- [Modeling Overview](index.md)
- [Forecasts Guide](../user-guide/forecasts-and-sensors.md)
