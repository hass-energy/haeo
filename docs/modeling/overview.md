# Linear Programming Overview

Introduction to linear programming and why it's ideal for energy optimization.

## What is Linear Programming?

LP finds optimal values for variables that minimize (or maximize) a linear objective subject to linear constraints.

**Mathematical form**:

$$
\begin{align}
\text{minimize} \quad & c^T x \\
\text{subject to} \quad & Ax \leq b \\
& Aeq \cdot x = beq \\
& lb \leq x \leq ub
\end{align}
$$

**Linearity requirement**: All relationships are straight lines - no $x^2$, $xy$, $\sin(x)$, etc.

## Key Components

**Decision variables** ($x$): What the optimizer chooses (power flows, battery SOC)

**Objective function** ($c^T x$): What to minimize (total cost)

**Constraints** ($Ax \leq b$, etc.): Requirements and limits (power balance, capacity)

## Why LP for Energy?

**Natural fit**:
- Power × Price = Cost (linear)
- Power × Time = Energy (linear)
- Sum of flows = Balance (linear)

**Fast solving**: Modern solvers (HiGHS) handle thousands of variables in seconds.

**Guaranteed optimal**: If feasible solution exists, LP finds global optimum.

**Scalability**: Handles large problems efficiently.

## HAEO's LP Problem

$$
\text{minimize} \quad \sum_{t=0}^{T-1} \left( P_{\text{import}}(t) \cdot p_{\text{import}}(t) - P_{\text{export}}(t) \cdot p_{\text{export}}(t) + \ldots \right)
$$

**Subject to**:
- Power balance: $\sum P_{\text{in}} = \sum P_{\text{out}}$ (equality)
- Energy balance: $E(t+1) = E(t) + \Delta E$ (equality)
- Power limits: $0 \leq P(t) \leq P_{\max}$ (inequality)
- Energy limits: $E_{\min} \leq E(t) \leq E_{\max}$ (inequality)

**Problem size**: ~4000 variables for typical 48h/5min setup.

**Solve time**: 0.5-2 seconds typical.

## Feasibility vs Optimality

**Feasible**: Satisfies all constraints (power balance, limits)

**Optimal**: Feasible with minimum cost

**Infeasible**: No solution exists (e.g., load exceeds maximum supply)

LP guarantees finding optimal if feasible.

## HAEO's Solver: HiGHS

**Why HiGHS**:
- Open source (MIT license)
- State-of-the-art performance
- Actively maintained
- Python bindings via PuLP

**Alternatives**: GLPK, CBC, Gurobi (commercial)

## Comparison with Other Approaches

| Approach | Speed | Global Optimum | Use Case |
|----------|-------|----------------|----------|
| **LP** (HAEO) | Very fast | Yes | Continuous decisions |
| MIP | Slower | Yes | On/off decisions |
| NLP | Slow | No (local) | Nonlinear physics |
| Heuristics | Variable | No | Complex non-convex |

**HAEO's choice**: LP is sufficient and much faster. Power flows are continuous, costs are linear.

## Limitations

**Cannot model directly**:
- On/off decisions (need MIP)
- Nonlinear efficiency curves
- Minimum runtime constraints

**HAEO's approach**: Linear approximations work well for energy systems.

## Related Documentation

- [Objective Function](objective-function.md)
- [Power Balance](power-balance.md)
- [Battery Modeling](battery.md)
- [Time Horizons](time-horizons.md)
