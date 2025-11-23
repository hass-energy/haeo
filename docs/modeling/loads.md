# Load Modeling

The Load element uses forecast data to model power consumption.
This unified approach handles both constant (fixed power) and time-varying consumption patterns.

## Model Formulation

### Decision Variables

None - follows forecast parameter.

### Parameters

| Parameter                | Dimensions | Source | Description                                   |
| ------------------------ | ---------- | ------ | --------------------------------------------- |
| $P_{\text{forecast}}(t)$ | $T$        | Sensor | Forecasted power consumption at time $t$ (kW) |

### Constraints

$$
P_{\text{load}}(t) = P_{\text{forecast}}(t) \quad \forall t
$$

Load follows forecast data exactly at each timestep.

### Cost Contribution

Loads do not contribute directly to the objective function.
Their cost impact is implicit through the energy required to satisfy their consumption.

## Physical Interpretation

Represents forecasted power consumption:

- **Constant loads**: Fixed power draw (provided via constant sensor value like `input_number`)
- **Forecasted loads**: Time-varying consumption predictions (whole-house historic average, scheduled loads, occupancy-based forecasts)

Loads are not controllable by the optimizer—they represent consumption that will occur regardless of optimization decisions.

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

<div class="grid cards" markdown>

- :material-file-document:{ .lg .middle } **User configuration guide**

    ---

    Configure loads in your Home Assistant setup.

    [:material-arrow-right: Load configuration](../user-guide/elements/load.md)

- :material-network:{ .lg .middle } **Network modeling**

    ---

    Understand how elements interact in the network model.

    [:material-arrow-right: Network modeling overview](index.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code for the load element model.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/load.py)

</div>
- [Forecasts Guide](../user-guide/forecasts-and-sensors.md)
