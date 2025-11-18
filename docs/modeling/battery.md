# Battery Modeling

This page explains how HAEO models battery storage systems using linear programming with a multi-section approach.

## Overview

A battery in HAEO is modeled as an energy storage device with:

- **Energy capacity**: Maximum stored energy
- **Power constraints**: Maximum charge/discharge rates
- **Multi-section SOC tracking**: Separate sections with different cost profiles
- **Efficiency losses**: Energy lost during charge/discharge cycles
- **Flexible operating ranges**: Preferred ranges with penalties for operation outside them

## Multi-Section Model Approach

HAEO uses a **multi-section battery model** instead of slack variables.
The battery's state of charge range is divided into sections, each with its own cumulative energy variables and cost structure:

1. **Undercharge section** (if configured): `[undercharge_percentage, min_charge_percentage]`
2. **Normal section** (always present): `[min_charge_percentage, max_charge_percentage]`
3. **Overcharge section** (if configured): `[max_charge_percentage, overcharge_percentage]`

### Key Semantic Change

- **`undercharge_percentage`** and **`overcharge_percentage`** are **absolute limits** (outer bounds)
- **`min_charge_percentage`** and **`max_charge_percentage`** are **preferred operating range** (inner bounds)

**Example configuration**:

```
undercharge=5% < min=10% < max=90% < overcharge=95%
```

This creates three sections where operation in the undercharge and overcharge zones incurs economic penalties.

## Model Formulation

### Decision Variables

For each section $n$ and time step $t \in \{0, 1, \ldots, T-1\}$:

- $E_{\text{charged}}^n(t)$: Cumulative energy charged into section $n$ (kWh, monotonically increasing)
- $E_{\text{discharged}}^n(t)$: Cumulative energy discharged from section $n$ (kWh, monotonically increasing)
- $P_{\text{charge}}(t)$: Total charging power (kW)
- $P_{\text{discharge}}(t)$: Total discharging power (kW)

### Parameters

**Required parameters**:

- $C$: Battery capacity (kWh) - `capacity`
- $E_{\text{initial}}$: Initial energy level (kWh) - derived from `initial_charge_percentage`
- $\text{SOC}_{\text{min}}$: Preferred minimum state of charge (%) - `min_charge_percentage` (default: 10%)
- $\text{SOC}_{\text{max}}$: Preferred maximum state of charge (%) - `max_charge_percentage` (default: 90%)
- $P_{\text{charge}}^{\max}$: Maximum charging power (kW) - `max_charge_power`
- $P_{\text{discharge}}^{\max}$: Maximum discharging power (kW) - `max_discharge_power`
- $\eta$: Round-trip efficiency (0-1) - `efficiency` (default: 0.99)
- $\Delta t$: Time step duration (hours) - `period`

**Optional section boundary parameters**:

- $\text{SOC}\_{\text{undercharge}}$: Absolute minimum state of charge (%) - `undercharge_percentage`
- $\text{SOC}\_{\text{overcharge}}$: Absolute maximum state of charge (%) - `overcharge_percentage`
- $c\_{\text{undercharge}}$: Cost penalty for discharging in undercharge section (\$/kWh) - `undercharge_cost`
- $c\_{\text{overcharge}}$: Cost penalty for charging in overcharge section (\$/kWh) - `overcharge_cost`

### Constraints

#### 1. Monotonicity Constraints

Cumulative energy variables can only increase over time:

$$
\begin{align}
E_{\text{charged}}^n(t) &\geq E_{\text{charged}}^n(t-1) \quad \forall n, t \\
E_{\text{discharged}}^n(t) &\geq E_{\text{discharged}}^n(t-1) \quad \forall n, t
\end{align}
$$

This ensures energy flows are unidirectional (charging increases charged energy, discharging increases discharged energy).

#### 2. Section Capacity Constraints

Each section's net energy must stay within its virtual capacity:

$$
0 \leq E_{\text{charged}}^n(t) - E_{\text{discharged}}^n(t) \leq C^n \quad \forall n, t
$$

Where $C^n$ is the virtual capacity of section $n$:

$$
C^n = C \cdot \frac{\text{SOC}\_{\text{upper}}^n - \text{SOC}\_{\text{lower}}^n}{100}
$$

**Example**: For a 10 kWh battery with normal section `[10%, 90%]`:

$$
C^{\text{normal}} = 10 \cdot \frac{90 - 10}{100} = 8 \text{ kWh}
$$

#### 3. Stacked SOC Ordering Constraints

Lower sections must be filled before higher sections can charge, and discharge in reverse order:

$$
\frac{E_{\text{charged}}^n(t) - E_{\text{discharged}}^n(t)}{C^n} \geq \frac{E_{\text{charged}}^{n+1}(t) - E_{\text{discharged}}^{n+1}(t)}{C^{n+1}} \quad \forall n < N, t
$$

This ensures that:

- Charging fills lower sections (undercharge → normal → overcharge)
- Discharging empties higher sections first (overcharge → normal → undercharge)

#### 4. Power Transfer Consistency Constraint

The sum of net energy changes across all sections equals the net power input:

$$
\sum_{n} \left[ \left( E_{\text{charged}}^n(t) - E_{\text{charged}}^n(t-1) \right) - \left( E_{\text{discharged}}^n(t) - E_{\text{discharged}}^n(t-1) \right) \right] = P_{\text{input}}(t) \cdot \Delta t
$$

Where the net power input includes efficiency:

$$
P_{\text{input}}(t) = P_{\text{charge}}(t) \cdot \sqrt{\eta} - \frac{P_{\text{discharge}}(t)}{\sqrt{\eta}}
$$

**Efficiency modeling**: The round-trip efficiency $\eta$ is split symmetrically between charging and discharging.
Using $\sqrt{\eta}$ for both operations ensures the combined round-trip efficiency equals $\eta$ exactly.

#### 5. Initial Energy Distribution

Initial energy is distributed across sections from bottom to top:

For initial SOC of $\text{SOC}_{\text{initial}}$%, sections fill sequentially until total energy is placed:

$$
E_{\text{total}}(0) = C \cdot \frac{\text{SOC}_{\text{initial}}}{100}
$$

**Example**: 50% SOC in a battery with sections `[5%-10%-90%-95%]` and capacity 10 kWh:

- Total initial energy: 5 kWh
- Undercharge section (5-10%): 0.5 kWh (full)
- Normal section (10-90%): 4.5 kWh (partial fill)
- Overcharge section (90-95%): 0 kWh (empty)

#### 6. Power Limits

Charging and discharging have maximum rates determined by the inverter and battery specifications:

$$
\begin{align}
0 \leq P_{\text{charge}}(t) &\leq P_{\text{charge}}^{\max} \\
0 \leq P_{\text{discharge}}(t) &\leq P_{\text{discharge}}^{\max}
\end{align}
$$

**Note**: The optimizer naturally avoids simultaneous charging and discharging as it would waste energy due to efficiency losses.

### Cost Contribution

Battery operation costs are calculated per section based on energy flow:

$$
\text{Battery Cost} = \sum_{n} \sum_{t=1}^{T-1} \left[ \Delta E_{\text{charged}}^n(t) \cdot c_{\text{charge}}^n(t) + \Delta E_{\text{discharged}}^n(t) \cdot c_{\text{discharge}}^n(t) \right]
$$

Where:

- $\Delta E_{\text{charged}}^n(t) = E_{\text{charged}}^n(t) - E_{\text{charged}}^n(t-1)$ is the energy charged into section $n$ during timestep $t$
- $\Delta E_{\text{discharged}}^n(t) = E_{\text{discharged}}^n(t) - E_{\text{discharged}}^n(t-1)$ is the energy discharged from section $n$ during timestep $t$

#### Cost Structure by Section

**Undercharge section** (if configured):

- Charge cost: Early charge incentive (encourages filling this section)
- Discharge cost: $c_{\text{undercharge}}$ (penalty for deep discharge)

**Normal section** (always present):

- Charge cost: Early charge incentive (small negative value that increases linearly over time to encourage later charging)
- Discharge cost: $c_{\text{discharge}}$ (standard degradation cost, if configured)

**Overcharge section** (if configured):

- Charge cost: $c_{\text{overcharge}}$ (penalty for overcharging)
- Discharge cost: $c_{\text{discharge}}$ (standard discharge cost)

**Economic interpretation**: The multi-section cost structure allows the optimizer to make economic trade-offs:

- Discharging into the undercharge section when grid prices are very high
- Charging into the overcharge section when grid prices are very low or excess solar is available
- Preferring the normal section for routine operation

## Physical Interpretation

### Multi-Section Energy Tracking

The multi-section model tracks cumulative energy flows rather than absolute stored energy:

**Section net energy** = **Cumulative charged** - **Cumulative discharged**

This approach:

- Eliminates the need for slack variables
- Naturally handles different cost zones through constraint structure
- Uses only linear constraints (no binary variables required)
- Enables efficient LP solving even with multiple sections

### State of Charge Calculation

Total battery SOC is computed from all sections:

$$
\text{SOC}(t) = \frac{\sum_n \left( E_{\text{charged}}^n(t) - E_{\text{discharged}}^n(t) \right)}{C} \times 100
$$

The stacked SOC ordering constraints ensure energy flows naturally:

- Charging fills from lowest to highest section
- Discharging empties from highest to lowest section

### Energy Flow Example

Consider a 10 kWh battery with configuration `[5%-10%-90%-95%]`:

**Charging from 8% to 92%**:

1. Fill undercharge section (5-10%): 0.2 kWh to reach 10%
2. Fill normal section (10-90%): 8.0 kWh to reach 90%
3. Partial fill overcharge section (90-92%): 0.2 kWh

The monotonicity and stacking constraints ensure this order automatically.

**Discharging from 92% to 8%**:

1. Empty overcharge section first (92-90%): -0.2 kWh
2. Empty normal section (90-10%): -8.0 kWh
3. Partial empty undercharge section (10-8%): -0.2 kWh

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

## Configuration Impact

### Capacity and SOC Range

- **Capacity**: Larger batteries provide more energy arbitrage opportunities but require longer charge/discharge windows
- **Normal section range** (`min_charge_percentage` to `max_charge_percentage`): Wider range gives more flexibility with no economic penalty
- **Section boundaries** (`undercharge_percentage`, `overcharge_percentage`): Extending absolute limits allows emergency operation with penalties

### Cost Configuration

- **Undercharge cost**: Higher values discourage deep discharge (battery protection)
- **Overcharge cost**: Higher values discourage full charge (battery longevity)
- **Balance with grid prices**: Set penalties relative to typical grid price volatility

**Example scenario**: If grid prices vary $0.05-0.50/kWh, setting `undercharge_cost=0.10` allows deep discharge when grid exceeds $0.10/kWh above baseline.

### Power Limits

- Tighter limits slow schedule response
- Higher limits require capable inverter hardware
- Asymmetric limits model different charge/discharge capabilities

### Efficiency

- Applied symmetrically: $\sqrt{\eta}$ for charging, $1/\sqrt{\eta}$ for discharging
- Affects all sections equally
- Higher efficiency directly reduces operational costs

## Related Documentation

- [Battery Configuration Guide](../user-guide/elements/battery.md) - User-facing configuration
- [Modeling Overview](index.md) - Overall optimization formulation
- [Units Documentation](../developer-guide/units.md) - Why we use kW/kWh

[:material-arrow-right: Continue to Grid Modeling](grid.md)
