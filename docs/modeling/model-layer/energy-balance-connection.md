# Energy Balance Connection

The `EnergyBalanceConnection` models lossless energy redistribution between adjacent storage partitions within a multi-partition storage device.
It enforces fill ordering (lower partitions fill before upper) and handles capacity changes through bidirectional power flow.

## Purpose

Multi-partition storage devices in HAEO separate usable capacity into lower and upper partitions.
The lower partition should fill before the upper partition to maximize value from limited cycling capacity.
When capacity changes (e.g., due to reserve adjustments), energy may need to redistribute between partitions.

The balance connection handles two scenarios:

1. **Downward flow**: Energy moves from upper to lower when there is room in the lower partition
2. **Upward flow**: Energy moves from lower to upper when capacity shrinks below current stored energy

## Model formulation

### Decision variables

For each time step $t$:

- $P_{\downarrow}(t)$: Power flowing downward from upper to lower (kW, positive)
- $P_{\uparrow}(t)$: Power flowing upward from lower to upper (kW, positive)
- $S_{\text{unmet}}(t)$: Slack variable for unmet demand (kW)
- $S_{\text{absorbed}}(t)$: Slack variable for absorbed excess (kW)

### Parameters

- $E_{\text{lower}}(t)$: Energy stored in lower partition (kWh)
- $E_{\text{upper}}(t)$: Energy stored in upper partition (kWh)
- $C_{\text{lower}}(t)$: Capacity of lower partition (kWh, fence-posted T+1 values)
- $\Delta t$: Period duration (hours)

Derived quantities:

- $\text{demand}(t) = C_{\text{lower}}(t) - E_{\text{lower}}(t)$: Room in lower partition
- $\text{available}(t) = E_{\text{upper}}(t)$: Energy available in upper partition
- $\text{excess}(t) = E_{\text{lower}}(t) - C_{\text{lower}}(t+1)$: Energy above next capacity

### Constraints

#### Downward flow

Downward flow implements $P_{\downarrow} \cdot \Delta t \geq \min(\text{demand}, \text{available})$:

$$
P_{\downarrow}(t) \cdot \Delta t \geq \text{demand}(t) - S_{\text{unmet}}(t) \cdot \Delta t
$$

$$
S_{\text{unmet}}(t) \cdot \Delta t \geq \text{demand}(t) - \text{available}(t)
$$

The slack variable $S_{\text{unmet}}$ allows the constraint to handle the case where demand exceeds available energy.
A cost penalty on the slack ensures it is minimized.

#### Upward flow

Upward flow implements $0 \leq P_{\uparrow} \cdot \Delta t \leq \max(0, \text{excess})$:

$$
P_{\uparrow}(t) \cdot \Delta t \leq \text{excess}(t) + S_{\text{absorbed}}(t) \cdot \Delta t
$$

$$
S_{\text{absorbed}}(t) \cdot \Delta t \geq -\text{excess}(t)
$$

The slack variable $S_{\text{absorbed}}$ absorbs negative excess values (when capacity is stable or growing).
A cost penalty on the slack ensures it is minimized.

### Cost function

The balance connection contributes a cost penalty for slack variables:

$$
\text{Cost} = \sum_{t} \left[ S_{\text{unmet}}(t) + S_{\text{absorbed}}(t) \right] \cdot \Delta t \cdot p_{\text{slack}}
$$

where $p_{\text{slack}}$ is the slack penalty.

The penalty must be larger than typical energy prices to ensure the slack variables are minimized to their theoretical minimum values, correctly implementing the min/max semantics.

## Physical interpretation

**Lossless transfer**:
Unlike power connections, balance connections have 100% efficiency.
Energy is redistributed within the same physical storage device, just between logical partitions.

**Fill ordering**:
By requiring downward flow to fill lower partition capacity, the model ensures lower partitions fill before upper partitions.
This maximizes value from limited cycling capacity.

**Capacity tracking**:
When storage reserve changes (e.g., user increases reserve during a storm), capacity may shrink.
Upward flow handles energy that must vacate the lower partition.

## Slack penalty selection

The default slack penalty is intentionally large.
It must exceed any reasonable energy price to ensure the LP solver minimizes slack variables even when there might be marginal cost benefits to leaving energy unbalanced.

## Next steps

<div class="grid cards" markdown>

- :material-battery-charging:{ .lg .middle } **Energy Storage model**

    ---

    Multi-partition storage formulation and SOC tracking.

    [:material-arrow-right: Energy Storage formulation](elements/energy-storage.md)

- :material-connection:{ .lg .middle } **Power connection**

    ---

    Standard bidirectional power flow connections.

    [:material-arrow-right: Connection formulation](connections/index.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code for the balance connection model.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/energy_balance_connection.py)

</div>
