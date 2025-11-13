# Load Modeling

The Load element uses forecast data to model power consumption.
This unified approach handles both constant (fixed power) and time-varying consumption patterns.

## Load Element

### Decision Variables

None - follows forecast parameter.

### Parameters

- $P_{\text{forecast}}(t)$: Forecasted power at time $t$ (kW) - from `forecast` sensors

### Constraints

$$
P_{\text{load}}(t) = P_{\text{forecast}}(t) \quad \forall t
$$

Load follows forecast data exactly at each timestep.

### Physical Interpretation

Represents any power consumption pattern:

- **Constant loads**: Baseline consumption (refrigerators, network equipment, standby power, always-on devices)
- **Variable loads**: Time-varying consumption (HVAC, cooking, EV charging, occupancy-based loads)

Forecast accuracy directly impacts optimization quality.

## Constant Behavior

When a sensor provides a constant value (e.g., an `input_number` helper), the load exhibits constant behavior:

$$
P_{\text{load}}(t) = P_{\text{constant}} \quad \forall t
$$

This is achieved by providing a sensor that reports the same value for all periods, not through special model handling.

## Multiple Loads

Total load at a balancing node equals the sum of all connected Load elements.
This allows modeling separate consumption components:

$$
P_{\text{total}}(t) = \sum_{i=1}^{N} P_{\text{load},i}(t)
$$

You can combine constant and variable loads by creating separate Load elements with different sensors.

## Configuration Impact

| Pattern  | Accuracy Needed | Best For                           |
| -------- | --------------- | ---------------------------------- |
| Constant | Rough estimate  | Simple setup, stable consumption   |
| Variable | High accuracy   | Time-varying loads, optimal timing |

**Overestimating load**: May cause infeasibility if supply can't meet demand.

**Underestimating load**: Real system may import more than optimized.

## Related Documentation

- [Load Configuration](../user-guide/elements/load.md)
- [Modeling Overview](index.md)
- [Forecasts Guide](../user-guide/forecasts-and-sensors.md)
