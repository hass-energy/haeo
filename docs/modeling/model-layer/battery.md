# Battery Model

This page explains how HAEO models battery storage systems using linear programming.

## Overview

A battery in HAEO's model layer is a single-section energy storage device with:

- **Energy capacity**: Maximum stored energy
- **Cumulative energy tracking**: Monotonically increasing charge/discharge variables
- **State of charge constraints**: Energy bounds within capacity
- **Power balance**: Integration with network through connections

!!! note "Multi-Section Batteries"

    Complex battery behavior (undercharge/normal/overcharge sections, early charge incentives, cost penalties) is implemented at the [device adapter layer](../device-layer/battery.md) by composing multiple Battery model instances with connections and a central node.

## Model Formulation

The battery model follows the [fence post pattern](../index.md#power-and-energy-discretization) used throughout HAEO's optimization.
Power variables (charge/discharge rates) represent average power over each period and have $T$ values indexed as $t \in \{0, 1, \ldots, T-1\}$.
Energy variables (stored energy) represent instantaneous values at time boundaries and have $T+1$ values indexed as $t \in \{0, 1, \ldots, T\}$.
Power is calculated from the change in energy between consecutive boundaries divided by the period duration.

### Decision Variables

For each time step $t \in \{0, 1, \ldots, T\}$ (note: $T+1$ time points for energy state):

- $E_{\text{in}}(t)$: Cumulative energy charged into battery (kWh, monotonically increasing)
- $E_{\text{out}}(t)$: Cumulative energy discharged from battery (kWh, monotonically increasing)

**Initial conditions**:

- $E_{\text{in}}(0)$: Initial charge level (constant, not a variable)
- $E_{\text{out}}(0) = 0$: Battery starts with zero cumulative discharge

### Parameters

**Required parameters**:

- $C(t)$: Battery capacity (kWh) at time boundary $t$ - `capacity`
- $E_{\text{initial}}$: Initial charge in kWh - `initial_charge`
- $\Delta t$: Time step duration (hours) - `period`

### Constraints

#### 1. Energy Flow Constraints

Cumulative energy variables can only increase over time (prevents energy flowing backward):

$$
\begin{align}
E_{\text{in}}(t+1) &\geq E_{\text{in}}(t) \quad \forall t \in [0, T-1] \\
E_{\text{out}}(t+1) &\geq E_{\text{out}}(t) \quad \forall t \in [0, T-1]
\end{align}
$$

This ensures energy flows are unidirectional (charging increases $E_{\text{in}}$, discharging increases $E_{\text{out}}$).

**Shadow prices**: The `energy_in_flow` and `energy_out_flow` shadow prices represent the marginal value of relaxing these constraints. Non-zero values are rare in practice since batteries naturally flow energy in one direction at a time.

#### 2. State of Charge Constraints

Net energy must stay within capacity:

$$
0 \leq E_{\text{in}}(t) - E_{\text{out}}(t) \leq C(t) \quad \forall t \in [1, T]
$$

**Shadow prices**:

- `soc_max`: Marginal value of additional storage capacity. Negative values indicate the battery is full and more capacity would reduce costs.
- `soc_min`: Marginal value of deeper discharge. Positive values indicate the battery is empty and the ability to extract more energy would reduce costs.

#### 3. Power Balance Constraint

Net battery power equals the power from network connections:

$$
P_{\text{connection}}(t) = P_{\text{charge}}(t) - P_{\text{discharge}}(t) \quad \forall t \in [0, T-1]
$$

Where:

- $P_{\text{connection}}(t)$ is the power from network connections (positive = charging, negative = discharging)
- $P_{\text{charge}}(t) = \frac{E_{\text{in}}(t+1) - E_{\text{in}}(t)}{\Delta t}$ is the charging power
- $P_{\text{discharge}}(t) = \frac{E_{\text{out}}(t+1) - E_{\text{out}}(t)}{\Delta t}$ is the discharging power

**Shadow price**: The `power_balance` shadow price represents the marginal value of power at the battery terminals.

### Cost Contribution

The single-section battery model has no inherent costs. Costs (efficiency losses, degradation, early charge incentives, penalties) are applied through [Connection](connection.md) elements in the device adapter layer.

## Physical Interpretation

### Cumulative Energy Tracking

The model tracks cumulative energy flows rather than absolute stored energy:

**Net stored energy** = **Cumulative charged** ($E_{\text{in}}$) - **Cumulative discharged** ($E_{\text{out}}$)

This approach:

- Eliminates the need for slack variables
- Uses only linear constraints (no binary variables required)
- Enables efficient LP solving

### Power Calculation

Power is derived from energy changes:

$$
\begin{align}
P_{\text{charge}}(t) &= \frac{E_{\text{in}}(t+1) - E_{\text{in}}(t)}{\Delta t} \\
P_{\text{discharge}}(t) &= \frac{E_{\text{out}}(t+1) - E_{\text{out}}(t)}{\Delta t}
\end{align}
$$

### Energy Flow Example

Consider a 10 kWh battery section with initial charge of 4 kWh:

**Initial state** ($t=0$):

- $E_{\text{in}}(0) = 4.0$ kWh (constant)
- $E_{\text{out}}(0) = 0.0$ kWh (constant)
- Net energy = 4.0 kWh

**After charging 2 kWh over 1 hour** ($t=1$):

- $E_{\text{in}}(1) = 6.0$ kWh (increased by 2)
- $E_{\text{out}}(1) = 0.0$ kWh (unchanged)
- Net energy = 6.0 kWh
- $P_{\text{charge}}(0) = (6.0 - 4.0) / 1.0 = 2.0$ kW

**After discharging 3 kWh over next hour** ($t=2$):

- $E_{\text{in}}(2) = 6.0$ kWh (unchanged)
- $E_{\text{out}}(2) = 3.0$ kWh (increased by 3)
- Net energy = 3.0 kWh
- $P_{\text{discharge}}(1) = (3.0 - 0.0) / 1.0 = 3.0$ kW

### Power Balance Integration

The battery participates in network power balance through the connection power:

$$
P_{\text{connection}}(t) = P_{\text{charge}}(t) - P_{\text{discharge}}(t)
$$

Where:

- **Positive** $P_{\text{connection}}$: Battery is charging (consuming power from network)
- **Negative** $P_{\text{connection}}$: Battery is discharging (providing power to network)

## Numerical Considerations

### Units

HAEO uses kW for power and kWh for energy:

- **Capacity**: 10 kWh (not 10000 Wh)
- **Power**: 5 kW (not 5000 W)
- **Time**: hours (not seconds)

This keeps variables in similar numerical ranges (0.001 to 1000) which:

- Improves solver performance
- Reduces numerical errors
- Makes debugging easier

See the [units documentation](../../developer-guide/units.md) for detailed explanation.

## Device Layer Integration

The single-section battery model is a building block for more complex battery behavior:

- **Multi-section batteries**: Multiple Battery instances connected through a node
- **Efficiency losses**: Applied through Connection efficiency parameters
- **Power limits**: Applied through Connection max_power constraints
- **Cost penalties**: Applied through Connection price parameters
- **Early charge incentives**: Applied through Connection time-varying prices

See the [Battery Device Layer documentation](../device-layer/battery.md) for how these are composed.

## Next Steps

<div class="grid cards" markdown>

- :material-file-document:{ .lg .middle } **User configuration guide**

    ---

    Configure batteries in your Home Assistant setup.

    [:material-arrow-right: Battery configuration](../../user-guide/elements/battery.md)

- :material-layers:{ .lg .middle } **Device layer**

    ---

    Understand how single-section batteries are composed into multi-section behavior.

    [:material-arrow-right: Battery device layer](../device-layer/battery.md)

- :material-network:{ .lg .middle } **Network modeling**

    ---

    Understand how elements interact in the network model.

    [:material-arrow-right: Network modeling overview](../index.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code for the battery model.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/battery.py)

</div>
