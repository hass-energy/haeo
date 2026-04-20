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

Connections compose ordered segments. See [segments](../segments/) for details on each type.

## Model formulation

### Decision variables

The Connection creates per-tag LP variables for the input power flow — one per tag per time step:

| Variable              | Domain                  | Description                               |
| --------------------- | ----------------------- | ----------------------------------------- |
| $P_{\\text{in},k}(t)$ | $\\mathbb{R}_{\\geq 0}$ | Power entering the connection for tag $k$ |

When no tags are specified, a single default tag is used (always-tagged paradigm).

Segments do **not** create their own variables (except SOC pricing, which creates auxiliary slack variables).
Instead, the Connection passes its power variables through the segment chain.
Each segment receives a `power_in` expression and exposes a `power_out` expression.

### Parameters

| Parameter  | Description                                                                                   |
| ---------- | --------------------------------------------------------------------------------------------- |
| `source`   | Name of the source element                                                                    |
| `target`   | Name of the target element                                                                    |
| `periods`  | Time period durations (hours)                                                                 |
| `segments` | Ordered mapping of segment names to segment specifications                                    |
| `tags`     | Set of tag IDs for per-source power decomposition (see [Tagged Power](../../tagged-power.md)) |

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
PricingSegment instances contribute energy costs to the primary objective (index 0).

Connections also contribute a time-preference term to the secondary objective (index 1).
Only **terminal** connections — those whose source element has `is_source=True` (produces power) or whose target element has `is_sink=True` (consumes power) — contribute to this term.
Pure transfer connections (e.g. an inverter's DC↔AC paths between two junction-style nodes) return `None` for the secondary so they do not steer the tie-breaker; otherwise the solver could saturate any zero-primary-cost loop to consume the secondary budget.

Each terminal connection computes a per-period magnitude

$$
m_{p,t} = (P \cdot T + 1) - \bigl(p \cdot T + (t + 1)\bigr)
$$

where $p$ is the connection's priority (auto-computed from sorted endpoint properties), $T$ is the number of periods, $t$ is the time step, and $P$ is the total number of connections in the network.
The magnitude is strictly positive, larger for earlier periods and lower-priority connections.

The **signed** weight applied to the secondary objective is then asymmetric across the two ends of the connection:

$$
w_{p,t} = -\mathbf{1}_{\text{target is sink}} \cdot m_{p,t} + \alpha \cdot \mathbf{1}_{\text{source is source}} \cdot m_{p,t}
$$

with $\alpha = \text{SOURCE\_PENALTY\_FACTOR} < 1$.
The secondary contribution for a connection is $\sum_t w_{p,t} \cdot P_{\text{in}}(t) \cdot \Delta t_t$.

- **Sink-terminal end** ($\text{target.is\_sink}=\text{True}$): the weight is strictly **negative** — every kWh of flow arriving at a sink reduces the secondary, so the solver prefers to consume (charge batteries, serve load, export) as early in the horizon as possible.
- **Source-terminal end** ($\text{source.is\_source}=\text{True}$): the weight is strictly **positive** with a smaller magnitude — every kWh of flow leaving a source increases the secondary, so the solver prefers to produce (discharge batteries, draw from the grid) as late in the horizon as possible.
- **Both ends terminal** (e.g. a battery round-trip connection): the two weights partly cancel, so phantom simultaneous charge+discharge no longer stacks into a double reward.

With $\alpha < 1$ the sink reward still dominates for a genuine source → sink path, so legitimate flow is incentivised; the scaled-down source penalty only prevents phantom round-trip flows from being doubly rewarded.
Connections with different priorities receive non-overlapping weight ranges: lower-priority connections are filled first.
Within a connection, earlier periods carry larger magnitudes than later ones, so ties are broken by pushing flow to the earliest (for sinks) or latest (for sources) feasible period.

The secondary objective does not affect the minimum cost — it only selects among cost-equivalent solutions.
The network solves this lexicographically: primary cost is minimised first, then the secondary objective is minimised subject to the primary remaining optimal.
A practical consequence is that cost-free opportunities at sinks are taken when available — for example, surplus solar charges a battery rather than being curtailed, even when no downstream revenue exists — while production capacity is held in reserve until it is needed.

## Outputs

Connection exposes power flow and segment outputs:

- `connection_power` — power flow through this connection
- `segments` — nested map of segment names to constraint shadow outputs

The `segments` output groups segment outputs using the segment names provided in the configuration.
Adapters use this map to surface segment-specific shadow prices.

## Tag decomposition

The connection decomposes its power flow into per-tag LP variables.
This enables [tagged power](../../tagged-power.md) tracking and per-source cost differentiation.

### Per-tag variables

For each tag $k$ in the tag set, a per-tag flow variable is created:

$$
P_{\text{in},k}(t) \geq 0 \quad \forall k \in \text{tags}, \; t \in [0, T-1]
$$

The total flow is the sum of all per-tag flows:

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

### Tag prices

Each entry in `tag_prices` adds a price for power flowing on a specific tag:

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
