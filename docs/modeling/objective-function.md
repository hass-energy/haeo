# Objective Function

HAEO minimizes total cost over the optimization horizon.

## Complete Formulation

$$
\text{minimize} \quad \sum_{t=0}^{T-1} \left( C_{\text{grid}}(t) + C_{\text{battery}}(t) + C_{\text{solar}}(t) \right)
$$

### Grid Costs

$$
C_{\text{grid}}(t) = \left( P_{\text{import}}(t) \cdot p_{\text{import}}(t) - P_{\text{export}}(t) \cdot p_{\text{export}}(t) \right) \cdot \Delta t
$$

Import is positive cost. Export is negative cost (revenue).

### Battery Costs

$$
C_{\text{battery}}(t) = \left( P_{\text{charge}}(t) \cdot c_{\text{charge}}(t) + P_{\text{discharge}}(t) \cdot c_{\text{discharge}} \right) \cdot \Delta t
$$

Where:
- $c_{\text{charge}}(t) = c_{\text{charge,base}} \cdot \frac{T-t}{T}$ (temporal diminishing)
- $c_{\text{discharge}}$ is constant

**Temporal diminishing**: Discourages early charging when future conditions are uncertain.

### Solar Costs

$$
C_{\text{solar}}(t) = P_{\text{solar}}(t) \cdot c_{\text{production}} \cdot \Delta t
$$

Usually $c_{\text{production}} = 0$.

## Why Minimization?

**Costs are positive**: Grid import, battery degradation.

**Revenue is negative cost**: Grid export, feed-in tariffs.

**Result**: Minimizing total gives lowest net cost (or maximum net revenue).

## Linearity

All terms are linear in decision variables:

$$
\text{Cost} = a_1 x_1 + a_2 x_2 + \ldots
$$

Where $a_i$ are constants (prices) and $x_i$ are variables (power flows).

Required for LP. Enables fast, guaranteed optimal solutions.

## Cost Components

**Required**:
- Grid import/export (always present)

**Optional**:
- Battery degradation (usually 0)
- Solar production price (usually 0)

**Not included** (constant, doesn't affect optimization):
- Load costs (fixed demand)
- Connection costs (lossless)

## Configuration Impact

| Parameter | Effect on Optimization |
|-----------|----------------------|
| Time-varying grid prices | Enables time-shifting value |
| Flat grid prices | Limited optimization benefit |
| Battery costs > 0 | Reduces cycling |
| Battery costs = 0 | Maximizes arbitrage |

**Price spreads**: Larger difference between peak/off-peak = more optimization value.

## Related Documentation

- [Grid Modeling](grid.md)
- [Battery Modeling](battery.md)
- [Time Horizons](time-horizons.md)
- [LP Overview](overview.md)
