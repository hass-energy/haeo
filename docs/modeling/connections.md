# Connection Modeling

Connections model bidirectional power flow paths between elements with optional limits, efficiency losses, and transfer costs.

## Model Formulation

### Decision Variables

For each time step $t$:

- $P_{s \rightarrow t}(t)$: Power flow from source to target (kW, positive)
- $P_{t \rightarrow s}(t)$: Power flow from target to source (kW, positive)

### Parameters

- $P_{s \rightarrow t}^{\max}(t)$: Maximum power from source to target (kW) - from `max_power_source_target` config
- $P_{t \rightarrow s}^{\max}(t)$: Maximum power from target to source (kW) - from `max_power_target_source` config
- $\eta_{s \rightarrow t}(t)$: Efficiency for source to target flow (0-1) - from `efficiency_source_target` config
- $\eta_{t \rightarrow s}(t)$: Efficiency for target to source flow (0-1) - from `efficiency_target_source` config
- $c_{s \rightarrow t}(t)$: Price for source to target flow (\$/kWh) - from `price_source_target` config
- $c_{t \rightarrow s}(t)$: Price for target to source flow (\$/kWh) - from `price_target_source` config
- Source element: Where power flows from
- Target element: Where power flows to

**Default values:**

- Missing power limits → unlimited (no constraint)
- Missing efficiency → 100% (no loss)
- Missing price → no cost

### Constraints

#### Power Limits

$$
0 \leq P_{s \rightarrow t}(t) \leq P_{s \rightarrow t}^{\max}(t) \quad \forall t
$$

$$
0 \leq P_{t \rightarrow s}(t) \leq P_{t \rightarrow s}^{\max}(t) \quad \forall t
$$

If limits are not specified, the upper bound is infinite (unlimited flow).

#### Power Balance Integration

Connection power participates in node balance with efficiency applied to incoming power:

**At source node:**

- Outflow: $-P_{s \rightarrow t}(t)$ (power leaving)
- Inflow: $+P_{t \rightarrow s}(t) \cdot \eta_{t \rightarrow s}(t)$ (power arriving with efficiency)

**At target node:**

- Inflow: $+P_{s \rightarrow t}(t) \cdot \eta_{s \rightarrow t}(t)$ (power arriving with efficiency)
- Outflow: $-P_{t \rightarrow s}(t)$ (power leaving)

**Key concept:**
Power leaving a node is not multiplied by efficiency, but power arriving at a node is multiplied by efficiency (losses occur during transmission).

### Cost Function

If pricing is configured, the connection contributes to the objective function:

$$
\text{Cost} = \sum_{t} \left[ c_{s \rightarrow t}(t) \cdot P_{s \rightarrow t}(t) + c_{t \rightarrow s}(t) \cdot P_{t \rightarrow s}(t) \right] \cdot \Delta t
$$

where $\Delta t$ is the time period in hours.

## Physical Interpretation

**Bidirectional flow:**
Both directions can be active simultaneously in the optimization model, though typically only one direction will have non-zero flow at any given time.
Misconfigurations can result in both being used, however, for example if you set up the connection such that it can arbitrage power between the two elements.

**Efficiency modeling:**
Represents real-world losses (inverter efficiency, transmission losses, etc.).
Applied to power arriving at destination.
Can vary over time.

**Pricing:**
Models transmission fees, wheeling charges, or connection costs.
Can vary over time.
Independent pricing for each direction.

## Use Cases

### Unidirectional Connection

Solar → Node (generation only):
Set only `max_power_source_target`.
Leave `max_power_target_source` unset (or set to 0).

### Bidirectional Connection

Grid ↔ Node (import/export):
Set both `max_power_source_target` and `max_power_target_source`.
Can have different limits in each direction.
Can have different efficiencies and prices.

### Inverter with Losses

DC Node ↔ AC Node:
Set power limits for both directions (inverter rating).
Set efficiency < 100% for both directions.
Efficiency can be asymmetric if needed.

### Connection with Transmission Fees

Node A ↔ Node B with wheeling charges:
Set power limits.
Set prices for one or both directions.
Prices can vary over time (peak/off-peak rates).

## Configuration Impact

| Configuration                  | Behavior                             |
| ------------------------------ | ------------------------------------ |
| Only `max_power_source_target` | Unidirectional flow only             |
| Both power limits set          | Bidirectional flow allowed           |
| No power limits                | Unlimited flow in both directions    |
| Efficiency < 100%              | Power losses during transmission     |
| Price set                      | Cost added to optimization objective |

## Related Documentation

<div class="grid cards" markdown>

- :material-file-document:{ .lg .middle } **User configuration guide**

    ---

    Configure connections in your Home Assistant setup.

    [:material-arrow-right: Connection configuration](../user-guide/elements/connections.md)

- :material-network:{ .lg .middle } **Network modeling**

    ---

    Understand how elements interact in the network model.

    [:material-arrow-right: Network modeling overview](index.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code for the connection model.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/connection.py)

</div>
