# Battery Modeling

This page explains how HAEO models battery storage systems using linear programming.

## Overview

A battery in HAEO is modeled as an energy storage device with:

- **Energy capacity**: Maximum stored energy
- **Power constraints**: Maximum charge/discharge rates
- **State of charge (SOC) tracking**: Energy level over time
- **Efficiency losses**: Energy lost during charge/discharge cycles
- **Operating range**: Minimum and maximum SOC limits

## Model Formulation

### Decision Variables

For each time step $t \in \{0, 1, \ldots, T-1\}$:

- $P_{\text{charge}}(t)$: Charging power (kW)
- $P_{\text{discharge}}(t)$: Discharging power (kW)
- $E(t)$: Energy stored in battery (kWh)

### Parameters

The battery model requires these configuration parameters:

- $C$: Battery capacity (kWh) - `capacity`
- $E_{\text{initial}}$: Initial energy level (kWh) - derived from `initial_charge_percentage`
- $\text{SOC}_{\min}$: Minimum state of charge (%) - `min_charge_percentage` (default: 10%)
- $\text{SOC}_{\max}$: Maximum state of charge (%) - `max_charge_percentage` (default: 90%)
- $P_{\text{charge}}^{\max}$: Maximum charging power (kW) - `max_charge_power`
- $P_{\text{discharge}}^{\max}$: Maximum discharging power (kW) - `max_discharge_power`
- $\eta$: Round-trip efficiency (0-1) - `efficiency` (default: 0.99)
- $\Delta t$: Time step duration (hours) - `period`

### Constraints

#### Energy Balance

The core of the battery model is the energy balance constraint.
It relates the battery's energy level across time steps:

$$
E(t+1) = E(t) + \left( P_{\text{charge}}(t) \cdot \sqrt{\eta} - \frac{P_{\text{discharge}}(t)}{\sqrt{\eta}} \right) \cdot \Delta t
$$

**Efficiency modeling**: The round-trip efficiency $\eta$ is split symmetrically between charging and discharging.
Using $\sqrt{\eta}$ for both operations ensures the combined round-trip efficiency equals $\eta$ exactly.

#### Initial Condition

The initial energy level is fixed (not optimized):

$$
E(0) = E_{\text{initial}} = C \cdot \frac{\text{initial\_charge\_percentage}}{100}
$$

#### SOC Limits

Energy must stay within the operational range to protect battery health:

$$
C \cdot \frac{\text{SOC}_{\min}}{100} \leq E(t) \leq C \cdot \frac{\text{SOC}_{\max}}{100} \quad \forall t
$$

#### Power Limits

Charging and discharging have maximum rates determined by the inverter and battery specifications:

$$
\begin{align}
0 \leq P_{\text{charge}}(t) &\leq P_{\text{charge}}^{\max} \\
0 \leq P_{\text{discharge}}(t) &\leq P_{\text{discharge}}^{\max}
\end{align}
$$

**Note**: The optimizer naturally avoids simultaneous charging and discharging as it would waste energy due to efficiency losses.

### Cost Contribution

Battery operation can include charge and discharge costs.
They model degradation:

$$
\text{Battery Cost} = \sum_{t=0}^{T-1} \left( P_{\text{charge}}(t) \cdot c_{\text{charge}} + P_{\text{discharge}}(t) \cdot c_{\text{discharge}} \right) \cdot \Delta t
$$

Where $c_{\text{charge}}$ and $c_{\text{discharge}}$ (in \$/kWh) represent the marginal cost of battery usage.

## Physical Interpretation

### Energy Balance

The energy balance equation captures the fundamental physics:

**Energy increase** = **Energy charged** - **Energy discharged** - **Losses**

Losses occur during both charging and discharging:

- **Charging**: Only $\eta\_{\text{charge}}$ of input energy is stored
- **Discharging**: Only $\eta\_{\text{discharge}}$ of stored energy is output

For symmetric modeling: $\eta*{\text{charge}} = \eta*{\text{discharge}} = \sqrt{\eta}$

This gives round-trip efficiency: $\eta*{\text{charge}} \times \eta*{\text{discharge}} = \eta$

### State of Charge

State of charge as a percentage:

$$
\text{SOC}(t) = \frac{E(t)}{C} \times 100
$$

HAEO tracks energy $E(t)$ directly, but SOC sensors report percentages.

### Power Balance Integration

The battery participates in network power balance as:

- **Positive terminal**: Discharge power (production)
- **Negative terminal**: Charge power (consumption)

Net power from battery perspective:

$$
P_{\text{battery}}(t) = P_{\text{discharge}}(t) - P_{\text{charge}}(t)
$$

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

See the [units documentation](../developer-guide/units.md) for detailed explanation.

### Efficiency Modeling

HAEO uses square-root efficiency to model symmetric losses:

$$
\eta_{\text{effective}} = \sqrt{\eta}
$$

**Example**: For 95% round-trip efficiency:

- Charge efficiency: $\sqrt{0.95} = 0.9747$
- Discharge efficiency: $1/\sqrt{0.95} = 1.026$
- Round-trip: $0.9747 \times (1/1.026) = 0.95$

This approach:

- Splits losses equally between charge and discharge
- Maintains exact round-trip efficiency
- Allows LP formulation (linear constraints)

## Configuration impact

Increasing capacity or widening the SOC range gives the optimizer more flexibility at the expense of longer charge and discharge windows and potentially faster battery wear.
Tighter power limits slow how quickly the schedule can respond, while higher limits require the supporting hardware to cope with the additional load.
Improving efficiency directly reduces losses because the model applies the factor on every charge and discharge cycle.

## Related Documentation

- [Battery Configuration Guide](../user-guide/elements/battery.md) - User-facing configuration
- [Modeling Overview](index.md) - Overall optimization formulation
- [Units Documentation](../developer-guide/units.md) - Why we use kW/kWh

[:material-arrow-right: Continue to Grid Modeling](grid.md)
