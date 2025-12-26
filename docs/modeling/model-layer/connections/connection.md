# Connection

The base `Connection` class models simple lossless bidirectional power flow between elements.
It provides the fundamental power variables and interface that all connection types share.

## Overview

Connection is the simplest connection type:

- **Lossless**: 100% efficiency in both directions
- **Unlimited**: No power limits by default
- **No cost**: Does not contribute to objective function

Use Connection when you need a simple power link without efficiency, limits, or pricing.
For more complex scenarios, use [PowerConnection](power-connection.md).

## Model Formulation

### Decision Variables

For each time step $t \in \{0, 1, \ldots, T-1\}$:

| Variable              | Domain                | Description                      |
| --------------------- | --------------------- | -------------------------------- |
| $P_{s \rightarrow t}$ | $\mathbb{R}_{\geq 0}$ | Power flow from source to target |
| $P_{t \rightarrow s}$ | $\mathbb{R}_{\geq 0}$ | Power flow from target to source |

Both variables are non-negative.
Net flow direction is determined by which variable is larger.

### Parameters

| Parameter | Description                   |
| --------- | ----------------------------- |
| `source`  | Name of the source element    |
| `target`  | Name of the target element    |
| `periods` | Time period durations (hours) |

### Constraints

The base Connection class adds no constraints.
Power variables are unbounded (except non-negativity).

### Power Balance Interface

Connections provide `power_into_source` and `power_into_target` properties that elements use for power balance:

**At source element:**

$$
P_{\text{into\_source}}(t) = P_{t \rightarrow s}(t) - P_{s \rightarrow t}(t)
$$

**At target element:**

$$
P_{\text{into\_target}}(t) = P_{s \rightarrow t}(t) - P_{t \rightarrow s}(t)
$$

Positive values indicate power flowing into the element.
Negative values indicate power flowing out.

### Cost Contribution

The base Connection class contributes no cost to the objective function.

## Physical Interpretation

**Lossless transfer:**
All power leaving one element arrives at the other.
No efficiency losses.

**Bidirectional capability:**
Power can flow in either direction at each time step.
The optimizer chooses the optimal direction based on costs elsewhere in the network.

**Interface abstraction:**
Elements don't need to know connection details.
They simply query `power_into_source` or `power_into_target` for their power balance.

## When to Use

Use the base Connection when:

- Connecting internal model elements with no losses
- Modeling ideal power transfers
- Building test fixtures

Use [PowerConnection](power-connection.md) instead when you need:

- Power limits
- Efficiency losses
- Transfer pricing

## Next Steps

<div class="grid cards" markdown>

- :material-power-plug:{ .lg .middle } **PowerConnection**

    ---

    Add limits, efficiency, and pricing.

    [:material-arrow-right: PowerConnection formulation](power-connection.md)

- :material-battery-charging:{ .lg .middle } **Elements**

    ---

    Battery and Node model elements.

    [:material-arrow-right: Element types](../elements/index.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/connection.py)

</div>
