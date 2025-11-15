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

**Required parameters**:

- $C$: Battery capacity (kWh) - `capacity`
- $E_{\text{initial}}$: Initial energy level (kWh) - derived from `initial_charge_percentage`
- $\text{SOC}_{\min}$: Minimum state of charge (%) - `min_charge_percentage` (default: 10%)
- $\text{SOC}_{\max}$: Maximum state of charge (%) - `max_charge_percentage` (default: 90%)
- $P_{\text{charge}}^{\max}$: Maximum charging power (kW) - `max_charge_power`
- $P_{\text{discharge}}^{\max}$: Maximum discharging power (kW) - `max_discharge_power`
- $\eta$: Round-trip efficiency (0-1) - `efficiency` (default: 0.99)
- $\Delta t$: Time step duration (hours) - `period`

**Optional soft limit parameters**:

- $\text{SOC}\_{\text{soft,min}}$: Soft minimum state of charge (%) - `undercharge_percentage`
- $\text{SOC}\_{\text{soft,max}}$: Soft maximum state of charge (%) - `overcharge_percentage`
- $c\_{\text{undercharge}}$: Undercharge cost penalty (\$/kWh) - `undercharge_cost`
- $c\_{\text{overcharge}}$: Overcharge cost penalty (\$/kWh) - `overcharge_cost`

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

These are **hard limits** enforced by variable bounds in the linear program.

#### Soft SOC Limits (Optional)

Batteries can be configured with **soft limits** to model preferred operating ranges with economic penalties for exceeding them:

- $\text{SOC}\_{\text{soft,min}}$: Soft minimum state of charge (%) - `undercharge_percentage`
- $\text{SOC}\_{\text{soft,max}}$: Soft maximum state of charge (%) - `overcharge_percentage`
- $c\_{\text{undercharge}}$: Cost penalty for operating below soft minimum (\$/kWh) - `undercharge_cost`
- $c\_{\text{overcharge}}$: Cost penalty for operating above soft maximum (\$/kWh) - `overcharge_cost`

These soft limits introduce **slack variables** that relax the soft constraints:

$$
\begin{align}
s\_{\text{under}}(t) &\geq 0 \quad \text{(undercharge slack)} \\
s\_{\text{over}}(t) &\geq 0 \quad \text{(overcharge slack)}
\end{align}
$$

**Soft limit constraints**:

The constraints work on the energy dynamics (power flows) rather than stored energy directly:

$$
\begin{align}
E(t-1) + \Delta E(t) + s\_{\text{under}}(t) &\geq C \cdot \frac{\text{SOC}\_{\text{soft,min}}}{100} \\
E(t-1) + \Delta E(t) - s\_{\text{over}}(t) &\leq C \cdot \frac{\text{SOC}\_{\text{soft,max}}}{100}
\end{align}
$$

where $\Delta E(t) = \left( P\_{\text{charge}}(t) \cdot \sqrt{\eta} - \frac{P\_{\text{discharge}}(t)}{\sqrt{\eta}} \right) \cdot \Delta t$ is the energy change.

The slack variables are bounded:

$$
\begin{align}
0 \leq s\_{\text{under}}(t) &\leq C \cdot \frac{\text{SOC}\_{\text{soft,min}} - \text{SOC}\_{\text{min}}}{100} \\
0 \leq s\_{\text{over}}(t) &\leq C \cdot \frac{\text{SOC}\_{\text{max}} - \text{SOC}\_{\text{soft,max}}}{100}
\end{align}
$$

These bounds ensure energy never exceeds the hard limits:

$$
\text{SOC}\_{\text{min}} \leq \text{SOC}\_{\text{soft,min}} < \text{SOC}\_{\text{soft,max}} \leq \text{SOC}\_{\text{max}}
$$

**Economic interpretation**: The optimizer can use the range outside soft limits when the marginal benefit (e.g., avoiding expensive grid imports) exceeds the penalty cost. This models scenarios like:

- Battery degradation from deep discharge/full charge cycles
- Safety margins for grid stability services
- Operational preferences with economic trade-offs

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

**With soft limits**, additional penalty costs apply:

$$
\text{Soft Limit Cost} = \sum_{t=0}^{T-1} \left( s\_{\text{under}}(t) \cdot c\_{\text{undercharge}} + s\_{\text{over}}(t) \cdot c\_{\text{overcharge}} \right)
$$

The slack variables $s\_{\text{under}}(t)$ and $s\_{\text{over}}(t)$ measure energy (kWh) outside preferred operating ranges.
These costs can be time-varying (forecasts) to model dynamic pricing scenarios.

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
