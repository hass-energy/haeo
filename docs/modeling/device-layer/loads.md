# Load Modeling

The Load element uses forecast data to model power consumption.
This unified approach handles both constant (fixed power) and time-varying consumption patterns.

Load creates a [SourceSink](../model-layer/source-sink.md) model (`is_source=false, is_sink=true`) plus an implicit [Connection](../model-layer/connection.md) that carries the consumption forecast as a fixed power requirement.

## Model Elements Created

```mermaid
graph LR
    subgraph "Device"
        SS["SourceSink<br/>(is_source=false, is_sink=true)"]
        Conn["Connection<br/>{name}:connection<br/>(fixed_power=true)"]
    end

    Node[Connection Target]

    SS <--|linked via| Conn
    Conn <--|connects to| Node
```

| Model Element                               | Name                | Parameters From Configuration       |
| ------------------------------------------- | ------------------- | ----------------------------------- |
| [SourceSink](../model-layer/source-sink.md) | `{name}`            | is_source=false, is_sink=true       |
| [Connection](../model-layer/connection.md)  | `{name}:connection` | forecast as fixed power requirement |

## Model Formulation

Load creates a SourceSink with `is_source=false, is_sink=true` (consumption only) plus a Connection with `fixed_power=true` that enforces the forecast:

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

- **Constant loads**: Fixed power draw (provided via constant forecast value)
- **Time-varying loads**: Consumption predictions (historical averages, scheduled loads, occupancy-based forecasts)

Loads are not controllable by the optimizer—they represent consumption that will occur regardless of optimization decisions.

Forecast accuracy directly impacts optimization quality.

## Constant Behavior

When the forecast provides a constant value, the load exhibits constant behavior:

$$
P_{\text{load}}(t) = P_{\text{constant}} \quad \forall t
$$

This is achieved by providing a forecast that reports the same value for all periods, not through special model handling.

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

## Next Steps

<div class="grid cards" markdown>

- :material-file-document:{ .lg .middle } **Load configuration**

    ---

    Configure loads in your Home Assistant setup.

    [:material-arrow-right: Load configuration](../../user-guide/elements/load.md)

- :material-power-plug:{ .lg .middle } **SourceSink model**

    ---

    Underlying model element for Load.

    [:material-arrow-right: SourceSink formulation](../model-layer/source-sink.md)

- :material-connection:{ .lg .middle } **Connection model**

    ---

    How consumption constraints are applied.

    [:material-arrow-right: Connection formulation](../model-layer/connection.md)

</div>
