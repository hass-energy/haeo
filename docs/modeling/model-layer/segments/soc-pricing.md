# SOC pricing segment

`SocPricingSegment` is the single SOC pricing model in HAEO.
It combines:

- **inventory pricing** (how far the battery is into a violation region), and
- **optional movement pricing** (how much movement enters or leaves that region).

This keeps the formulation linear (LP), while giving practical control over both depth and motion.

## Model formulation

### Parameters

| Parameter          | Description                      | Units  |
| ------------------ | -------------------------------- | ------ |
| $E_{thr}(t)$       | SOC threshold (model coordinate) | kWh    |
| $c_{dis}^{inv}(t)$ | Below-threshold inventory price  | \$/kWh |
| $c_{chg}^{inv}(t)$ | Above-threshold inventory price  | \$/kWh |
| $c_{dis}^{mov}(t)$ | Discharge movement price         | \$/kWh |
| $c_{chg}^{mov}(t)$ | Charge movement price            | \$/kWh |
| $E_{stored}(t)$    | Battery stored energy            | kWh    |

### Decision variables

| Variable     | Domain                | Description                                           |
| ------------ | --------------------- | ----------------------------------------------------- |
| $S_{dis}(t)$ | $\mathbb{R}_{\geq 0}$ | Below-threshold slack (violation depth)               |
| $S_{chg}(t)$ | $\mathbb{R}_{\geq 0}$ | Above-threshold slack (violation depth)               |
| $U_{dis}(t)$ | $\mathbb{R}_{\geq 0}$ | Movement entering/deepening below-threshold violation |
| $V_{dis}(t)$ | $\mathbb{R}_{\geq 0}$ | Movement recovering below-threshold violation         |
| $U_{chg}(t)$ | $\mathbb{R}_{\geq 0}$ | Movement entering/deepening above-threshold violation |
| $V_{chg}(t)$ | $\mathbb{R}_{\geq 0}$ | Movement recovering above-threshold violation         |

Movement variables are created only when movement pricing is configured.

### Constraints

Violation depth slacks:

$$
S_{dis}(t) \ge E_{thr}(t) - E_{stored}(t)
$$

$$
S_{chg}(t) \ge E_{stored}(t) - E_{thr}(t)
$$

Movement decomposition:

$$
S_{dis}(0)=U_{dis}(0)-V_{dis}(0)
$$

$$
S_{dis}(t)-S_{dis}(t-1)=U_{dis}(t)-V_{dis}(t), \quad t \ge 1
$$

$$
S_{chg}(0)=U_{chg}(0)-V_{chg}(0)
$$

$$
S_{chg}(t)-S_{chg}(t-1)=U_{chg}(t)-V_{chg}(t), \quad t \ge 1
$$

### Cost contribution

Inventory part:

$$
\sum_t \left( S_{dis}(t)c_{dis}^{inv}(t) + S_{chg}(t)c_{chg}^{inv}(t) \right)
$$

Optional movement part:

$$
\sum_t \left(
U_{dis}(t)c_{dis}^{mov}(t) + V_{dis}(t)c_{chg}^{mov}(t) +
U_{chg}(t)c_{chg}^{mov}(t) + V_{chg}(t)c_{dis}^{mov}(t)
\right)
$$

When movement pricing is enabled, HAEO adds a tiny slack regularization term to keep slacks at the minimum feasible values.

## Practical limitations

- LP cannot represent exact state-conditional throughput gating without binaries.
- Movement pricing is horizon-coupled through slack deltas, so far-horizon behavior can look less intuitive than near-term operation.
- If movement pricing is configured without meaningful inventory pricing, behavior can become less stable because movement terms depend on slack trajectory quality.
- This is still a soft-cost approach, not a hard prohibition.

## LP vs MILP option

If HAEO offered MILP as an option:

- **Expressiveness**: MILP can model exact on/off gating logic for state-conditional flow pricing (using binary variables and big-M or indicator constraints).
- **Fidelity**: MILP would match the intended “price flow only when inside region” behavior exactly.
- **Performance**: solve times and memory usage would typically increase significantly, especially for long horizons and multiple priced zones.
- **Operational complexity**: users would need solver capability checks, fallback handling, and potentially mode-specific defaults/tuning.

Recommended strategy is LP as default, with MILP as an advanced opt-in for cases where exact gating fidelity is worth the extra solve cost.
