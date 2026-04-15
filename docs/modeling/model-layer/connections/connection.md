# Connection

The `Connection` class models unidirectional power flow between elements.
It composes ordered segments that apply efficiency, limits, and pricing to the flow.
Bidirectional paths are modelled as two separate Connection elements.

## Overview

Connection is the primary model for power flow:

- **Unidirectional**: Each connection flows from `source` to `target`.
- **Composable**: Ordered segment chain defines behavior.
- **Lossless by default**: A passthrough segment is created when no segments are provided.
- **Extensible**: Segment outputs are exposed for adapters and diagnostics.

Segments are provided as an ordered mapping.
The mapping keys become segment names and drive the nested `segments` output.

## Segment types

- **[SOC pricing segment](../segments/soc-pricing.md)** applies SOC penalty costs.
- **[Efficiency segment](../segments/efficiency.md)** applies an efficiency multiplier.
- **[Power limit segment](../segments/power-limit.md)** enforces power limits.
- **[Pricing segment](../segments/pricing.md)** adds cost terms to the objective.
- **[Passthrough segment](../segments/passthrough.md)** forwards flow without constraints or cost.

## Model formulation

### Decision variables

The Connection creates LP variables for the input power flow — one per time step:

| Variable        | Domain                | Description                   |
| --------------- | --------------------- | ----------------------------- |
| $P_{\text{in}}$ | $\mathbb{R}_{\geq 0}$ | Power entering the connection |

Segments do **not** create their own variables (except SOC pricing, which creates auxiliary slack variables).
Instead, the Connection passes its power variables through the segment chain.
Each segment receives a `power_in` expression and exposes a `power_out` expression.

### Parameters

| Parameter    | Description                                                |
| ------------ | ---------------------------------------------------------- |
| `source`     | Name of the source element                                 |
| `target`     | Name of the target element                                 |
| `periods`    | Time period durations (hours)                              |
| `segments`   | Ordered mapping of segment names to segment specifications |
| `tags`       | Set of tag IDs for per-source power decomposition (see [Tagged Power](../../tagged-power.md)) |
| `tag_costs`  | Per-tag cost adjustments (list of `{tag, price}` dicts)    |

If `segments` is omitted or empty, a passthrough segment is created automatically.
Segment parameters can be scalars or per-period arrays.
Scalar values are broadcast across all periods.

### Functional segment composition

Segments are **functional transforms** on power expressions. The Connection chains them:

```python
flow = power_in  # The only LP variables (one per time step)
for segment in chain:
    flow = segment.power_out  # Each segment transforms the flow
    # Segments add constraints/costs as side effects
    # Most return input unchanged (identity transforms)
    # Efficiency returns input * factor (an expression, not a new variable)
power_out = flow  # Final output expression
```

This eliminates all inter-segment linking constraints. The variable count equals
the connection flow decisions (T) plus any auxiliary variables (e.g., SOC slack).

### Constraints

Each segment contributes constraints during construction.
Power limits constrain the input expressions.
No linking constraints between segments are needed.

### Power balance interface

Connections provide `power_into_source` and `power_into_target` properties that elements use for power balance:

$$P_{\text{into\_source}}(t) = -P_{\text{in}}(t)$$

$$P_{\text{into\_target}}(t) = P_{\text{out}}(t)$$

Power leaves the source and enters the target.
Efficiency losses are applied inside the segment chain.

### Cost contribution

Connection aggregates cost expressions from all segments.
PricingSegment instances contribute energy costs to the objective.

## Outputs

Connection exposes power flow and segment outputs:

- `connection_power` — power flow through this connection
- `segments` — nested map of segment names to constraint shadow outputs

The `segments` output groups segment outputs using the segment names provided in the configuration.
Adapters use this map to surface segment-specific shadow prices.

## Tag decomposition

When `tags` are provided, the connection decomposes its power flow into per-tag LP variables.
This enables [tagged power](../../tagged-power.md) tracking and per-source cost differentiation.

### Per-tag variables

For each tag $k$ in the tag set, a per-tag flow variable is created:

$$
P_{\text{in},k}(t) \geq 0 \quad \forall k \in \text{tags}, \; t \in [0, T-1]
$$

A sum constraint ensures the per-tag flows equal the total flow:

$$
P_{\text{in}}(t) = \sum_{k \in \text{tags}} P_{\text{in},k}(t)
$$

### Per-tag segment transforms

Segments that transform power (e.g., efficiency) are applied proportionally to each tag flow.
For an efficiency segment with factor $\eta$:

$$
P_{\text{out},k}(t) = P_{\text{in},k}(t) \cdot \eta
$$

The sum of per-tag outputs equals the segment's total output.

### Tag costs

Each entry in `tag_costs` adds a cost for power flowing on a specific tag:

$$
\text{Cost}_k = \sum_t c_k \cdot P_{\text{in},k}(t) \cdot \Delta t
$$

This enables per-source pricing (e.g., charging a premium for battery-sourced power exported to the grid).

### Per-tag power balance interface

Connections provide per-tag versions of the power balance interface used by elements:

$$P_{\text{into\_source},k}(t) = -P_{\text{in},k}(t)$$

$$P_{\text{into\_target},k}(t) = P_{\text{out},k}(t)$$

## Bidirectional paths

To model bidirectional flow (e.g., grid import/export), create two connections:

- A **forward** connection from source to target
- A **reverse** connection from target to source

Each connection has its own segment chain with independent parameters.
The adapter layer is responsible for combining outputs from both connections
into the appropriate device-level outputs (e.g., grid import power, grid export power).

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

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/core/model/elements/connection.py)

</div>
