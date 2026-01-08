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

| Variable            | Created When     | Domain                | Description                      |
| ------------------- | ---------------- | --------------------- | -------------------------------- |
| $P_{\text{in}}(t)$  | `is_sink=true`   | $\mathbb{R}_{\geq 0}$ | Power accepted from network (kW) |
| $P_{\text{out}}(t)$ | `is_source=true` | $\mathbb{R}_{\geq 0}$ | Power provided to network (kW)   |

**Note**: Variables are only created when needed based on the flags.
A pure junction (`is_source=false, is_sink=false`) creates no power variables.

### Parameters

Node has no direct parameters.
All operational parameters (power limits, efficiency, pricing) are configured on the connected [Connection](../connections/index.md) elements.

### Constraints

#### Power Balance

The power balance constraint depends on the Node configuration:

**Source and Sink** (`is_source=true, is_sink=true`):

$$
P_{\text{connection}}(t) + P_{\text{out}}(t) - P_{\text{in}}(t) = 0
$$

Power from connections plus generated power minus consumed power equals zero.

**Source Only** (`is_source=true, is_sink=false`):

$$
P_{\text{connection}}(t) + P_{\text{out}}(t) = 0
$$

All generated power must flow out through connections.

**Sink Only** (`is_source=false, is_sink=true`):

$$
P_{\text{connection}}(t) - P_{\text{in}}(t) = 0
$$

All consumed power must flow in through connections.

**Junction** (`is_source=false, is_sink=false`):

$$
P_{\text{connection}}(t) = 0
$$

Net connection power must be zero (Kirchhoff's law).

Where $P_{\text{connection}}(t)$ is the sum of power flows from all connected [Connection](../connections/index.md) elements, accounting for efficiency losses.

### Cost Contribution

Node contributes no direct cost to the objective function.
Costs are applied through the connected [Connection](../connections/index.md) elements via their pricing parameters.

## Physical Interpretation

**Source behavior**: Represents power generation capacity.
The actual generation is bounded by the Connection's `max_power_source_target` parameter (the forecast for PV, or import limit for Grid).

**Sink behavior**: Represents power consumption capacity.
The actual consumption is bounded by the Connection's `max_power_target_source` parameter (the forecast for Load, or export limit for Grid).

**Junction behavior**: Represents an electrical bus or node where power must balance.
Used to connect multiple elements at a common point (Kirchhoff's law).

## Next Steps

<div class="grid cards" markdown>

- :material-battery-charging:{ .lg .middle } **Energy Storage model**

    ---

    Energy storage with SOC dynamics.

    [:material-arrow-right: Energy Storage formulation](energy-storage.md)

- :material-connection:{ .lg .middle } **Connections**

    ---

    Power flow paths between elements.

    [:material-arrow-right: Connection types](../connections/index.md)

- :material-file-document:{ .lg .middle } **Device configuration**

    ---

    Configure Grid, Solar, Load, and Node elements.

    [:material-arrow-right: Elements overview](../../../user-guide/elements/index.md)

</div>
