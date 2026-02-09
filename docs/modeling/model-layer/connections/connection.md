# Connection

The `Connection` class models bidirectional power flow between elements.
It composes ordered segments that apply efficiency, limits, and pricing to the flow.

## Overview

Connection is the primary model for power flow:

- **Composable**: Ordered segment chain defines behavior.
- **Lossless by default**: A passthrough segment is created when no segments are provided.
- **Extensible**: Segment outputs are exposed for adapters and diagnostics.

Segments are provided as an ordered mapping.
The mapping keys become segment names and drive the nested `segments` output.

## Segment types

- **[SOC pricing segment](../segments/soc-pricing.md)** applies SOC penalty costs.
- **[Efficiency segment](../segments/efficiency.md)** applies direction-specific efficiency multipliers.
- **[Power limit segment](../segments/power-limit.md)** enforces directional limits and time-slice coupling.
- **[Pricing segment](../segments/pricing.md)** adds directional cost terms to the objective.
- **[Demand pricing segment](../segments/demand-pricing.md)** adds peak demand charges from price schedules.
- **[Passthrough segment](../segments/passthrough.md)** forwards flow without constraints or cost.

## Model formulation

### Decision variables

For each time step $t \in \{0, 1, \ldots, T-1\}$:

| Variable              | Domain                | Description                      |
| --------------------- | --------------------- | -------------------------------- |
| $P_{s \rightarrow t}$ | $\mathbb{R}_{\geq 0}$ | Power flow from source to target |
| $P_{t \rightarrow s}$ | $\mathbb{R}_{\geq 0}$ | Power flow from target to source |

These variables represent the input to the first segment in the chain.
Each segment may transform the flow before passing it to the next segment.

### Parameters

| Parameter  | Description                                                |
| ---------- | ---------------------------------------------------------- |
| `source`   | Name of the source element                                 |
| `target`   | Name of the target element                                 |
| `periods`  | Time period durations (hours)                              |
| `segments` | Ordered mapping of segment names to segment specifications |

If `segments` is omitted or empty, a passthrough segment is created automatically.
Segment parameters can be scalars or per-period arrays.
Scalar values are broadcast across all periods.

### Constraints

Connection adds linking constraints between adjacent segments.
Each segment contributes its own constraints, such as power limits or time-slice coupling.

### Power balance interface

Connections provide `power_into_source` and `power_into_target` properties that elements use for power balance.
These use the first segment inputs and last segment outputs:

$$
P_{\text{into\_source}}(t) = P^{\text{out}}_{t \rightarrow s,\text{last}}(t) - P^{\text{in}}_{s \rightarrow t,\text{first}}(t)
$$

$$
P_{\text{into\_target}}(t) = P^{\text{out}}_{s \rightarrow t,\text{last}}(t) - P^{\text{in}}_{t \rightarrow s,\text{first}}(t)
$$

Efficiency losses are applied inside the segment chain.
Elements do not need to account for them directly.

### Cost contribution

Connection aggregates cost expressions from all segments.
PricingSegment instances contribute directional energy costs.
DemandPricingSegment instances contribute peak demand costs.

## Outputs

Connection exposes power flow and segment outputs:

- `connection_power_source_target`
- `connection_power_target_source`
- `segments` (nested map of segment names to constraint shadow outputs)

The `segments` output groups segment outputs using the segment names provided in the configuration.
Adapters use this map to surface segment-specific shadow prices (for example `power_limit.source_target`).

## When to use

Use Connection for all power-flow paths.
Select the segment chain that matches the physical behavior you need.

## Next Steps

<div class="grid cards" markdown>

- :material-layers:{ .lg .middle } **Segments**

    ---

    Segment catalog and formulations.

    [:material-arrow-right: Segment index](../segments/index.md)

- :material-battery-charging:{ .lg .middle } **Elements**

    ---

    Battery and Node model elements.

    [:material-arrow-right: Element types](../elements/index.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/elements/connection.py)

</div>
