# Node Model

The Node model element represents power sources, sinks, and junction points in the network.
It provides a unified formulation for elements that produce power, consume power, or simply route power between connections.

## Overview

Node is a versatile model element controlled by two flags:

| `is_source` | `is_sink` | Behavior                           |
| ----------- | --------- | ---------------------------------- |
| `true`      | `true`    | Can both produce and consume power |
| `true`      | `false`   | Can only produce power             |
| `false`     | `true`    | Can only consume power             |
| `false`     | `false`   | Pure junction (routes power only)  |

Power limits and pricing are configured on the [Connection](../connections/index.md) to/from the Node, not on the Node itself.
This design separates the element's role (source, sink, or junction) from its operational constraints (limits, efficiency, cost).

## Model Formulation

### Decision Variables

For each time step $t \in \{0, 1, \ldots, T-1\}$:

| Variable                 | Created When     | Domain                | Description                      |
| ------------------------ | ---------------- | --------------------- | -------------------------------- |
| $P_{\text{produced}}(t)$ | `is_source=true` | $\mathbb{R}_{\geq 0}$ | Power provided to network (kW)   |
| $P_{\text{consumed}}(t)$ | `is_sink=true`   | $\mathbb{R}_{\geq 0}$ | Power accepted from network (kW) |

Variables are always created for both production and consumption.
Non-source nodes create zero-bounded production variables; non-sink nodes create zero-bounded consumption variables.

### Parameters

| Parameter       | Type               | Description                                                                           |
| --------------- | ------------------ | ------------------------------------------------------------------------------------- |
| `outbound_tags` | `set[int] \| None` | Tags that produced power can be placed on (see [Tagged Power](../../tagged-power.md)) |
| `inbound_tags`  | `set[int] \| None` | Tags that consumed power can draw from (None = all tags)                              |

Operational parameters (power limits, efficiency, pricing) are configured on the connected [Connection](../connections/index.md) elements.

### Constraints

#### Power Balance

The power balance constraint depends on the Node configuration:

**Source and Sink** (`is_source=true, is_sink=true`):

Per-tag power balance is enforced by the [tag balance constraint](../../tagged-power.md#per-tag-balance).
Both $P_{\text{produced}}$ and $P_{\text{consumed}}$ are unbounded.

**Source Only** (`is_source=true, is_sink=false`):

$$
P_{\text{connection}}(t) + P_{\text{produced}}(t) = 0
$$

All produced power must flow out through connections.

**Sink Only** (`is_source=false, is_sink=true`):

$$
P_{\text{connection}}(t) - P_{\text{consumed}}(t) = 0
$$

All consumed power must flow in through connections.

**Junction** (`is_source=false, is_sink=false`):

$$
P_{\text{connection}}(t) = 0
$$

Net connection power must be zero (Kirchhoff's law).

Where $P_{\text{connection}}(t)$ is the sum of power flows from all connected [Connection](../connections/index.md) elements, accounting for efficiency losses.

#### Tag Balance

The Element base class creates per-tag power balance constraints for all elements with tagged connections.
See the [tagged power formulation](../../tagged-power.md#per-tag-balance) for details.

### Cost Contribution

Node contributes no direct cost to the objective function.
Costs are applied through the connected [Connection](../connections/index.md) elements via their pricing parameters.

## Physical Interpretation

**Source behavior**: Represents power generation capacity.
The actual generation is bounded by the Connection's `max_power_source_target` parameter (the forecast for PV, or import limit for Grid).
Production is placed on `outbound_tags` for [tagged power](../../tagged-power.md) routing.

**Sink behavior**: Represents power consumption capacity.
The actual consumption is bounded by the Connection's `max_power_target_source` parameter (the forecast for Load, or export limit for Grid).
Consumption draws from `inbound_tags` for tagged power routing.

**Junction behavior**: Represents an electrical bus or node where power must balance.
Used to connect multiple elements at a common point (Kirchhoff's law).

## Next Steps

<div class="grid cards" markdown>

- :material-battery-charging:{ .lg .middle } **Battery model**

    ---

    Energy storage with SOC dynamics.

    [:material-arrow-right: Battery formulation](battery.md)

- :material-connection:{ .lg .middle } **Connections**

    ---

    Power flow paths between elements.

    [:material-arrow-right: Connection types](../connections/index.md)

- :material-file-document:{ .lg .middle } **Device configuration**

    ---

    Configure Grid, Solar, Load, and Node elements.

    [:material-arrow-right: Elements overview](../../../user-guide/elements/index.md)

</div>
