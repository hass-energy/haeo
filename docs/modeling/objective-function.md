# Objective Function

This page explains how HAEO formulates the cost minimization problem in its linear programming model.

## Overview

The objective function is the mathematical expression that HAEO **minimizes** during optimization.
It represents the total cost of operating the energy system over the optimization horizon.

Key characteristics:

- **Minimization problem**: Lower cost is better
- **Linear function**: Sum of terms (required for LP)
- **Time-based**: Costs accumulate over all time periods
- **Multi-component**: Different entities contribute different cost terms

By minimizing this objective function while satisfying all constraints (power balance, energy limits, etc.), HAEO finds the most economical way to operate your energy system.

## Complete Formulation

The total cost HAEO minimizes is:

$$
\text{Total Cost} = \sum_{t=0}^{T-1} \left( C_{\text{grid}}(t) + C_{\text{battery}}(t) + C_{\text{solar}}(t) \right)
$$

Breaking down each component:

### Grid Costs

$$
C_{\text{grid}}(t) = P_{\text{import}}(t) \cdot p_{\text{import}}(t) \cdot \Delta t - P_{\text{export}}(t) \cdot p_{\text{export}}(t) \cdot \Delta t
$$

Where:

- $P_{\text{import}}(t)$: Power imported from grid (kW)
- $p_{\text{import}}(t)$: Import price (\$/kWh)
- $P_{\text{export}}(t)$: Power exported to grid (kW)
- $p_{\text{export}}(t)$: Export price (\$/kWh)
- $\Delta t$: Time period (hours)

**Sign convention**: Export revenue is negative cost (reduces total cost).

### Battery Storage Costs

$$
C_{\text{battery}}(t) = P_{\text{charge}}(t) \cdot c_{\text{charge}}(t) \cdot \Delta t + P_{\text{discharge}}(t) \cdot c_{\text{discharge}} \cdot \Delta t
$$

Where:

- $P_{\text{charge}}(t)$: Battery charging power (kW)
- $c_{\text{charge}}(t)$: Charge cost (\$/kWh), varies with time using temporal diminishing
- $P_{\text{discharge}}(t)$: Battery discharging power (kW)
- $c_{\text{discharge}}$: Discharge cost (\$/kWh), constant

**Temporal diminishing**: Charge costs decrease over time to discourage early charging when future conditions are uncertain.
This is implemented as:

$$
c_{\text{charge}}(t) = c_{\text{charge,base}} \cdot \frac{T-t}{T}
$$

Early periods have higher effective charge cost, discouraging premature battery cycling.

### Solar Production Costs

$$
C_{\text{solar}}(t) = P_{\text{solar}}(t) \cdot c_{\text{production}} \cdot \Delta t
$$

Where:

- $P_{\text{solar}}(t)$: Solar generation (kW)
- $c_{\text{production}}$: Production price (\$/kWh, typically 0)

**Rarely used**: Most configurations set this to 0, as solar generation is "free" and its value is captured through reduced grid import.

### Complete Expression

Combining all terms:

$$
\begin{align}
\text{Total Cost} = \sum_{t=0}^{T-1} \Bigg( & P_{\text{import}}(t) \cdot p_{\text{import}}(t) - P_{\text{export}}(t) \cdot p_{\text{export}}(t) \\
& + P_{\text{charge}}(t) \cdot c_{\text{charge}}(t) + P_{\text{discharge}}(t) \cdot c_{\text{discharge}} \\
& + P_{\text{solar}}(t) \cdot c_{\text{production}} \Bigg) \cdot \Delta t
\end{align}
$$

This is a **linear** function of all the decision variables ($P_{\text{import}}$, $P_{\text{export}}$, $P_{\text{charge}}$, etc.), which is required for linear programming.

## Mathematical Detail

### Why Minimization?

HAEO minimizes cost rather than maximizes revenue because:

1. **Standard LP convention**: Most optimization problems are framed as minimization
2. **Natural accounting**: Costs are positive, revenue is negative cost
3. **Combined metric**: Single objective captures both spending and earning

**Revenue as negative cost**: When you export to the grid or have feed-in tariffs, these create negative cost terms, effectively increasing the objective (making it less negative = better).

### Linearity Requirement

For linear programming, the objective function must be **linear** in the decision variables:

$$
f(x_1, x_2, \ldots) = a_1 x_1 + a_2 x_2 + \ldots + b
$$

Where $a_i$ are constants (prices, costs) and $x_i$ are decision variables (power flows).

**Non-linear terms not allowed**:

- ❌ $P^2$: Quadratic costs
- ❌ $P_1 \cdot P_2$: Product of variables
- ❌ $\sqrt{P}$: Non-linear functions
- ❌ $\max(P_1, P_2)$: Non-differentiable functions

**Why this matters**: LP solvers are extremely efficient for linear problems but cannot handle non-linear objectives without transformation to mixed-integer programming (MIP) or other techniques.

### Cost Components Breakdown

**Required components**:

- Grid import cost (always present)
- Grid export revenue (usually present)

**Optional components**:

- Battery charge cost (models degradation, usually 0)
- Battery discharge cost (models degradation, usually 0)
- Solar production price (rarely used, usually 0)

**Not included** (implicitly optimized):

- Load costs: Loads are fixed, so their cost is constant and doesn't affect optimization
- Connection costs: Connections have no inherent cost (lossless)
- Net entity costs: Nets are virtual and have no cost

## Physical Interpretation

### Economic Optimization

The objective function captures the economic goal:

**Minimize**: Total spending on electricity
**Maximize** (implicitly): Total revenue from electricity sales

The optimal solution finds the power flow strategy that results in the lowest net cost over the optimization horizon.

### Time-Based Costs

Costs accumulate over time:

$$
\text{Cost per period} \times \text{Number of periods} = \text{Total cost}
$$

For a 48-hour horizon with 5-minute periods:

- $T = 576$ periods
- Each period: $\Delta t = 5/60 = 0.0833$ hours
- Total costs sum across all 576 periods

### Cost vs Revenue

**Positive costs** (increase objective):

- Grid imports during expensive periods
- Battery degradation costs
- Any generation costs

**Negative costs** (decrease objective, i.e., revenue):

- Grid exports during good prices
- Feed-in tariff payments
- Any revenue from generation

**Net cost** = Total positive costs - Total revenue

### Optimization Trade-offs

The objective function drives these trade-offs:

1. **Import timing**: Pay less by importing during cheap periods
2. **Export timing**: Earn more by exporting during expensive periods
3. **Battery cycling**: Balance degradation costs vs price arbitrage value
4. **Solar curtailment**: Avoid negative export prices by reducing generation

## Example: 24-Hour Cost Calculation

Consider a simple system over 24 hours:

**Configuration**:

- Battery: 10 kWh, charge/discharge cost: \$0.01/kWh
- Solar: 5 kW average, no production cost
- Load: 3 kW constant

**Price schedule**:

- Off-peak (00:00-07:00): Import \$0.10/kWh, Export \$0.05/kWh
- Peak (17:00-21:00): Import \$0.40/kWh, Export \$0.05/kWh
- Other: Import \$0.20/kWh, Export \$0.05/kWh

### Optimization Strategy

**Off-peak (00:00-07:00)**: 7 hours

- Import 5 kW to charge battery
- Meet 3 kW load
- Net import: 8 kW

$$
C_{\text{off-peak}} = 8 \times 7 \times 0.10 = \$5.60
$$

$$
C_{\text{battery}} = 5 \times 7 \times 0.01 = \$0.35 \text{ (charge cost)}
$$

**Daytime (07:00-17:00)**: 10 hours

- Solar: 5 kW
- Load: 3 kW
- Export: 2 kW

$$
C_{\text{daytime}} = -2 \times 10 \times 0.05 = -\$1.00 \text{ (revenue)}
$$

**Peak (17:00-21:00)**: 4 hours

- Battery discharge: 5 kW
- Load: 3 kW
- Export: 2 kW

$$
C_{\text{battery}} = 5 \times 4 \times 0.01 = \$0.20 \text{ (discharge cost)}
$$

$$
C_{\text{peak}} = -2 \times 4 \times 0.05 = -\$0.40 \text{ (revenue)}
$$

**Evening (21:00-24:00)**: 3 hours

- Solar: 0 kW
- Import: 3 kW
- Load: 3 kW

$$
C_{\text{evening}} = 3 \times 3 \times 0.20 = \$1.80
$$

### Total Cost Calculation

$$
\begin{align}
\text{Total Cost} &= C_{\text{off-peak}} + C_{\text{daytime}} + C_{\text{peak}} + C_{\text{evening}} + C_{\text{battery}} \\
&= 5.60 - 1.00 - 0.40 + 1.80 + 0.35 + 0.20 \\
&= \$6.55
\end{align}
$$

**Without optimization** (import all load at average price \$0.225/kWh):

$$
\text{Cost}_{\text{naive}} = 3 \times 24 \times 0.225 = \$16.20
$$

**Savings**: $\$16.20 - \$6.55 = \$9.65$ per day (60% reduction)

## Implementation Details

### PuLP Objective

HAEO builds the objective function using PuLP:

```python
from pulp import LpProblem, LpMinimize, lpSum

# Create problem
prob = LpProblem("Energy_Optimization", LpMinimize)

# Add objective function
prob += lpSum([entity.cost() for entity in entities])

# Each entity returns its cost contribution
```

### Entity Cost Methods

Each entity type implements a `cost()` method:

**Grid entity**:

```python
def cost(self):
    import_cost = lpSum(
        power_import[t] * price_import[t] * period
        for t in range(n_periods)
    )
    export_revenue = lpSum(
        power_export[t] * price_export[t] * period
        for t in range(n_periods)
    )
    return import_cost - export_revenue  # Revenue is negative cost
```

**Battery entity**:

```python
def cost(self):
    charge_cost = lpSum(
        power_charge[t] * charge_cost[t] * period  # Temporal diminishing
        for t in range(n_periods)
    )
    discharge_cost = lpSum(
        power_discharge[t] * discharge_cost * period
        for t in range(n_periods)
    )
    return charge_cost + discharge_cost
```

### Temporal Diminishing

Battery charge costs use temporal diminishing:

```python
charge_cost_sequence = np.linspace(0, charge_cost_base, n_periods)
```

This creates a linearly decreasing cost:

- Period 0: `charge_cost_base` (highest)
- Period T-1: 0 (lowest)

Encourages charging later when prices are more certain.

## Numerical Considerations

### Units Consistency

All costs must use consistent units:

- Power: kW
- Energy: kWh = kW × hours
- Price: \$/kWh
- Time: hours
- **Result**: \$ (dollars)

Example verification:

$$
\text{Cost} = \underbrace{5}_{\text{kW}} \times \underbrace{0.25}_{\$/\text{kWh}} \times \underbrace{0.0833}_{\text{hours}} = 0.104 \text{ \$}
$$

### Cost Magnitude

Typical daily costs:

- Small home: \$2-5
- Average home: \$5-15
- Large home: \$10-30
- Commercial: \$50-500+

Objective function values are typically in this range.

### Solver Tolerance

LP solvers minimize to a tolerance (e.g., 1e-6):

- Optimal cost: \$12.345678
- Reported cost: \$12.35 (rounded for display)
- **Difference**: Negligible for practical purposes

## Configuration Impact

### Grid Pricing

**Time-varying prices**:

- ✅ Enables optimization value
- ✅ Battery becomes profitable
- ✅ Strategic timing is important

**Flat pricing**:

- ❌ Limited optimization value
- ❌ Battery only useful for solar storage
- ❌ No time-shifting benefit

### Battery Degradation Costs

**Zero costs** (default):

- Battery cycles freely
- Only grid prices matter
- Maximum optimization flexibility

**Non-zero costs**:

- Discourages excessive cycling
- Models real degradation economics
- May reduce battery utilization

**Typical values**:

- $c_{\text{charge}} = c_{\text{discharge}} = \$0.01-0.05/kWh$
- Represents amortized degradation cost
- Actual value depends on battery chemistry and lifespan

### Solar Production Price

**Zero** (default):

- Solar is "free"
- Value is implicit in reduced grid import
- Simplest configuration

**Non-zero positive**:

- Models feed-in tariff separate from export
- Incentivizes generation
- Rarely used

**Negative**:

- Models solar contract costs
- Very unusual

## Related Documentation

- [Grid Modeling](grid.md) - How grid costs are formulated
- [Battery Modeling](battery.md) - Battery degradation costs
- [Photovoltaics Modeling](photovoltaics.md) - Solar production pricing
- [Time Horizons](time-horizons.md) - How costs accumulate over time

## Next Steps

Explore related modeling topics:

- [Power Balance](power-balance.md) - Constraints that the optimization must satisfy
- [Time Horizons](time-horizons.md) - How the optimization period affects costs
- [Battery Modeling](battery.md) - How batteries enable cost reduction

[:octicons-arrow-right-24: Continue to Power Balance](power-balance.md)
