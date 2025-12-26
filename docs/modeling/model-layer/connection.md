# Connection Model

Connections model power flow paths between elements.
HAEO provides a `Connection` base class for lossless flow and specialized subclasses for additional constraints.

## Connection class hierarchy

**Connection** (base class):
Models lossless bidirectional power flow between elements.
Provides the fundamental power variables and interface that all connections share.

**PowerConnection** (extends Connection):
Adds optional power limits, efficiency losses, and transfer costs.
This is the primary connection type for most user-configured connections.

**BatteryBalanceConnection**:
Models lossless energy redistribution between battery sections.
Used internally by the Battery device to balance energy across SOC sections.

## Connection (base class)

The base `Connection` class models simple lossless bidirectional power flow.

### Decision variables

For each time step $t$:

- $P_{s \rightarrow t}(t)$: Power flow from source to target (kW, non-negative)
- $P_{t \rightarrow s}(t)$: Power flow from target to source (kW, non-negative)

### Power balance interface

Connections provide `power_into_source` and `power_into_target` properties for node balance calculations:

**At source element:**

$$
P_{\text{into\_source}}(t) = P_{t \rightarrow s}(t) - P_{s \rightarrow t}(t)
$$

**At target element:**

$$
P_{\text{into\_target}}(t) = P_{s \rightarrow t}(t) - P_{t \rightarrow s}(t)
$$

The base Connection class applies no efficiency losses (100% efficiency in both directions).

## PowerConnection formulation

PowerConnection extends Connection to add power limits, efficiency losses, and transfer pricing.

### Parameters

- $P_{s \rightarrow t}^{\max}(t)$: Maximum power from source to target (kW) - from `max_power_source_target` config
- $P_{t \rightarrow s}^{\max}(t)$: Maximum power from target to source (kW) - from `max_power_target_source` config
- $\eta_{s \rightarrow t}(t)$: Efficiency for source to target flow (0-1) - from `efficiency_source_target` config
- $\eta_{t \rightarrow s}(t)$: Efficiency for target to source flow (0-1) - from `efficiency_target_source` config
- $c_{s \rightarrow t}(t)$: Price for source to target flow (\$/kWh) - from `price_source_target` config
- $c_{t \rightarrow s}(t)$: Price for target to source flow (\$/kWh) - from `price_target_source` config

**Default values:**

- Missing power limits → unlimited flow (no constraint)
- Zero power limit → no flow allowed in that direction
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

PowerConnection overrides the base Connection's power balance to apply efficiency losses.
Efficiency is applied to power arriving at the destination:

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
Leave `max_power_target_source` unset, or set to 0 to explicitly prevent reverse flow.

!!! tip "Modeling Hybrid Inverters"

    Connections are an effective way to model hybrid inverters.
    A hybrid inverter connects DC (battery/solar) and AC (grid/loads) sides with bidirectional power flow.
    Set power limits in both directions to the inverter's rating and apply appropriate efficiency losses.

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
| No power limits (unset)        | Unlimited flow in both directions    |
| Power limit = 0                | No flow allowed in that direction    |
| Efficiency < 100%              | Power losses during transmission     |
| Price set                      | Cost added to optimization objective |

## Next Steps

<div class="grid cards" markdown>

- :material-file-document:{ .lg .middle } **User configuration guide**

    ---

    Configure connections in your Home Assistant setup.

    [:material-arrow-right: Connection configuration](../../user-guide/elements/connections.md)

- :material-network:{ .lg .middle } **Network modeling**

    ---

    Understand how elements interact in the network model.

    [:material-arrow-right: Network modeling overview](../index.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code for the PowerConnection model.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/power_connection.py)

</div>
