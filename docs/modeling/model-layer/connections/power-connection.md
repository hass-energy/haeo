# PowerConnection profile

PowerConnection is now a connection profile implemented by the [Connection](connection.md) segment chain.
There is no separate PowerConnection class.
This page describes the standard combination of segments used to model limits, efficiency, and pricing.

## Overview

The PowerConnection profile composes these segments:

- **PowerLimitSegment** for directional capacity and time-slice coupling
- **EfficiencySegment** for direction-specific losses
- **PricingSegment** for directional cost contributions

## Model formulation

### Decision variables

The profile inherits the base Connection variables:

| Variable              | Domain                | Description                      |
| --------------------- | --------------------- | -------------------------------- |
| $P_{s \rightarrow t}$ | $\mathbb{R}_{\geq 0}$ | Power flow from source to target |
| $P_{t \rightarrow s}$ | $\mathbb{R}_{\geq 0}$ | Power flow from target to source |

### Segment parameters

This profile uses a segment chain with these parameters:

| Segment           | Parameter                  | Default   | Description                              |
| ----------------- | -------------------------- | --------- | ---------------------------------------- |
| PowerLimitSegment | `max_power_source_target`  | Unlimited | Maximum power from source to target (kW) |
| PowerLimitSegment | `max_power_target_source`  | Unlimited | Maximum power from target to source (kW) |
| PowerLimitSegment | `fixed`                    | False     | Enforce equality instead of inequality   |
| EfficiencySegment | `efficiency_source_target` | 1.0       | Source to target efficiency (ratio)      |
| EfficiencySegment | `efficiency_target_source` | 1.0       | Target to source efficiency (ratio)      |
| PricingSegment    | `price_source_target`      | None      | Price for source to target flow (\$/kWh) |
| PricingSegment    | `price_target_source`      | None      | Price for target to source flow (\$/kWh) |

Device-layer adapters accept efficiency in percent and convert to ratios.
All segment parameters can be time-varying arrays.

### Constraints

#### Power limits

When power limits are configured:

$$
0 \leq P_{s \rightarrow t}(t) \leq P_{s \rightarrow t}^{\max}(t) \quad \forall t
$$

$$
0 \leq P_{t \rightarrow s}(t) \leq P_{t \rightarrow s}^{\max}(t) \quad \forall t
$$

If `fixed=True`, these become equality constraints (power must equal the limit).

**Shadow prices**: The `connection_shadow_power_max_source_target` and `connection_shadow_power_max_target_source` outputs provide the marginal value of relaxing these constraints.

#### Time-slice constraint

When both power limits are set, the power-limit segment adds a time-slice constraint preventing simultaneous flow at full capacity in both directions:

$$
\frac{P_{s \rightarrow t}(t)}{P_{s \rightarrow t}^{\max}(t)} + \frac{P_{t \rightarrow s}(t)}{P_{t \rightarrow s}^{\max}(t)} \leq 1 \quad \forall t
$$

This models physical limitations of bidirectional devices (e.g., inverters that can't simultaneously charge and discharge at full rate).

### Power balance interface

The efficiency segment applies losses to the power balance:

**At source element:**

$$
P_{\text{into\_source}}(t) = P_{t \rightarrow s}(t) \cdot \eta_{t \rightarrow s}(t) - P_{s \rightarrow t}(t)
$$

**At target element:**

$$
P_{\text{into\_target}}(t) = P_{s \rightarrow t}(t) \cdot \eta_{s \rightarrow t}(t) - P_{t \rightarrow s}(t)
$$

**Key concept:**
Power leaving an element is not multiplied by efficiency, but power arriving at an element is multiplied by efficiency (losses occur during transmission).

### Cost function

If pricing is configured, the pricing segment contributes to the objective function:

$$
\text{Cost} = \sum_{t} \left[ c_{s \rightarrow t}(t) \cdot P_{s \rightarrow t}(t) + c_{t \rightarrow s}(t) \cdot P_{t \rightarrow s}(t) \right] \cdot \Delta t
$$

where $\Delta t$ is the time period in hours.

## Physical interpretation

**Bidirectional flow:**
Both directions can be active simultaneously in the optimization model.
Misconfigurations can allow arbitrage if pricing is inconsistent.

**Efficiency modeling:**
Losses are applied to power arriving at the destination.
Efficiency can vary over time and by direction.

**Pricing:**
Pricing models transmission fees, wheeling charges, or connection costs.
It can vary over time and by direction.

## Typical uses

Use this profile for:

- Grid import and export (pricing plus limits)
- Inverters (efficiency plus limits)
- Loads and solar (fixed power limit in one direction)

Device-layer elements supply the segment values for these cases.

## Next Steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connection model**

    ---

    Segment-based connection formulation.

    [:material-arrow-right: Connection formulation](connection.md)

- :material-file-document:{ .lg .middle } **Connection configuration**

    ---

    Configure connections in Home Assistant.

    [:material-arrow-right: Connection configuration](../../../user-guide/elements/connections.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/elements/connection.py)

</div>
