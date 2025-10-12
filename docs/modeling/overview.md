# Linear Programming Overview

This page provides a detailed introduction to linear programming (LP) and why it's the perfect optimization approach for energy systems like HAEO.

## Overview

Linear programming is an optimization technique for finding the best solution to problems where:

- The **objective** (what you want to optimize) is a linear function
- The **constraints** (requirements and limits) are linear equations or inequalities
- The **variables** (decisions to make) can take any value within their bounds

HAEO uses LP to determine optimal power flows in your energy system that minimize cost while respecting all physical and operational constraints.

## What is Linear Programming?

### Mathematical Definition

A linear program aims to:

$$
\begin{align}
\text{minimize} \quad & c^T x \\
\text{subject to} \quad & Ax \leq b \\
& Aeq \cdot x = beq \\
& lb \leq x \leq ub
\end{align}
$$

Where:

- $x$: Decision variables (what we optimize)
- $c$: Cost coefficients (objective function)
- $A, b$: Inequality constraint matrices
- $Aeq, beq$: Equality constraint matrices
- $lb, ub$: Lower and upper bounds

**Linearity requirement**: All terms are linear in $x$ (no $x^2$, $xy$, $\sin(x)$, etc.)

### Why "Linear"?

**Linear** means the relationship is a straight line (or hyperplane in higher dimensions):

$$
f(x_1, x_2) = a_1 x_1 + a_2 x_2 + b
$$

**Not linear** (quadratic):

$$
f(x_1, x_2) = x_1^2 + x_2^2 \quad \text{❌}
$$

**Not linear** (product):

$$
f(x_1, x_2) = x_1 \cdot x_2 \quad \text{❌}
$$

**Why it matters**: Linear problems have unique mathematical properties that make them efficiently solvable.

## Key Components

### 1. Decision Variables

**Definition**: Values the optimizer chooses to minimize the objective.

**In HAEO**:

- $P_{\text{import}}(t)$: How much to import from grid at time $t$
- $P_{\text{export}}(t)$: How much to export to grid
- $P_{\text{charge}}(t)$: Battery charging power
- $P_{\text{discharge}}(t)$: Battery discharging power
- $E(t)$: Battery energy level
- $P_{\text{solar}}(t)$: Solar generation (if curtailment enabled)

**Not variables in HAEO**:

- Load power (fixed by forecast)
- Prices (parameters, not decisions)
- Solar generation without curtailment (fixed by forecast)

**Example**: For a 48-hour horizon with 5-minute periods and 4 entities:

- ~4000 decision variables
- Optimizer finds optimal values for all simultaneously

### 2. Objective Function

**Definition**: What we want to minimize (or maximize).

**In HAEO**: Total cost over optimization horizon

$$
\text{minimize} \quad \sum_{t=0}^{T-1} \left( C_{\text{grid}}(t) + C_{\text{battery}}(t) + C_{\text{solar}}(t) \right)
$$

**Linear form**:

$$
\text{minimize} \quad \sum_{t=0}^{T-1} \left( c_1 P_{\text{import}}(t) + c_2 P_{\text{export}}(t) + c_3 P_{\text{charge}}(t) + \ldots \right)
$$

All terms are linear: coefficient × variable.

### 3. Constraints

**Definition**: Requirements and limits that must be satisfied.

**Types in HAEO**:

**Equality constraints** (must hold exactly):

- Power balance: $\sum P_{\text{in}}(t) = \sum P_{\text{out}}(t)$
- Energy balance: $E(t+1) = E(t) + \Delta E(t)$

**Inequality constraints** (limits):

- Power limits: $0 \leq P(t) \leq P_{\max}$
- Energy limits: $E_{\min} \leq E(t) \leq E_{\max}$
- Connection limits: $P_{\min} \leq P_c(t) \leq P_{\max}$

**Bound constraints** (variable limits):

- Non-negativity: $P(t) \geq 0$
- Capacity limits: Built into variable definitions

All constraints are **linear** in the decision variables.

## Why LP for Energy Optimization?

### Perfect Fit for Energy Systems

**1. Natural linearity**:

- Power × Price = Cost (linear)
- Power × Time = Energy (linear)
- Sum of flows = Balance (linear)

**2. Physical constraints are linear**:

- Power limits: $P \leq P_{\max}$ ✓
- Energy balance: $E_{t+1} = E_t + \Delta E$ ✓
- Power balance: $\sum P_{\text{in}} = \sum P_{\text{out}}$ ✓

**3. Computational efficiency**:

- Very fast solving (milliseconds to seconds)
- Scales to large problems
- Guaranteed global optimum

### Advantages of LP

**Guaranteed optimal solution**:

- If a feasible solution exists, LP finds the global optimum
- No local minima to get stuck in
- Deterministic results

**Fast solving**:

- Modern solvers (HiGHS, GLPK, Gurobi) are extremely efficient
- Thousands of variables solved in seconds
- Suitable for real-time optimization

**Provable properties**:

- Can detect infeasibility (no solution exists)
- Can detect unboundedness (infinite solutions)
- Provides optimality guarantees

**Scalability**:

- Handles large problems well
- Adding more entities doesn't dramatically slow solving
- Sparse matrices exploit problem structure

## HAEO's Optimization Problem

### Complete Formulation

HAEO solves this LP at each optimization cycle:

$$
\begin{align}
\text{minimize} \quad & \sum_{t=0}^{T-1} \Bigg( P_{\text{import}}(t) \cdot p_{\text{import}}(t) - P_{\text{export}}(t) \cdot p_{\text{export}}(t) \\
& \quad + P_{\text{charge}}(t) \cdot c_{\text{charge}}(t) + P_{\text{discharge}}(t) \cdot c_{\text{discharge}} \\
& \quad + P_{\text{solar}}(t) \cdot c_{\text{production}} \Bigg) \cdot \Delta t
\end{align}
$$

**Subject to**:

Power balance constraints:

$$
\sum_{c \in \mathcal{C}_{\text{in}}} P_c(t) = \sum_{c \in \mathcal{C}_{\text{out}}} P_c(t) \quad \forall t, \forall \text{ nets}
$$

Battery energy balance:

$$
E(t+1) = E(t) + \left( P_{\text{charge}}(t) \cdot \sqrt{\eta} - \frac{P_{\text{discharge}}(t)}{\sqrt{\eta}} \right) \cdot \Delta t \quad \forall t
$$

Power limits:

$$
\begin{align}
0 \leq P_{\text{import}}(t) &\leq P_{\text{import}}^{\max} \\
0 \leq P_{\text{export}}(t) &\leq P_{\text{export}}^{\max} \\
0 \leq P_{\text{charge}}(t) &\leq P_{\text{charge}}^{\max} \\
0 \leq P_{\text{discharge}}(t) &\leq P_{\text{discharge}}^{\max}
\end{align}
$$

Energy limits:

$$
E_{\min} \leq E(t) \leq E_{\max} \quad \forall t
$$

Connection limits:

$$
P_{\min} \leq P_c(t) \leq P_{\max} \quad \forall t, \forall \text{ connections}
$$

### Problem Size

**Typical HAEO problem** (48h horizon, 5min periods, medium system):

- **Variables**: ~4000
- **Equality constraints**: ~3000 (power balance + energy balance)
- **Inequality constraints**: ~8000 (bounds on variables)
- **Solve time**: 0.5-2 seconds

**Large system** (multiple batteries, buildings, etc.):

- **Variables**: ~10000
- **Constraints**: ~20000
- **Solve time**: 2-10 seconds

Still very fast for real-time optimization!

## Feasibility vs Optimality

### Feasibility

A solution is **feasible** if it satisfies all constraints:

- Power balance holds at all times
- All limits are respected
- Energy conservation is maintained

**Infeasible problem**: No solution exists that satisfies all constraints.

**Common causes of infeasibility**:

- Load exceeds maximum possible generation + import
- Battery limits too restrictive for energy requirements
- Conflicting connection limits

### Optimality

A solution is **optimal** if it:

- Is feasible (satisfies all constraints)
- Has the minimum objective function value among all feasible solutions

**LP guarantee**: If a feasible solution exists, LP finds the optimal one.

### Example: Feasible vs Optimal

**Scenario**: 3 kW load, 5 kW battery, grid prices vary

**Feasible solution 1**: Import all load from grid

- Cost: $3 \times 24 \times 0.25 = \$18.00$
- Feasible ✓ (all constraints satisfied)
- Optimal? ❌ (battery not used)

**Feasible solution 2**: Use battery to shift consumption

- Cost: $\$9.50$ (optimized timing)
- Feasible ✓
- Optimal ✓ (LP proves this is minimum cost)

## How LP Solvers Work

### Simplex Method

**Classic algorithm** (Dantzig, 1947):

1. Start at a corner point of feasible region
2. Move along edges to adjacent corners
3. Choose direction that improves objective
4. Stop when no improving direction exists

**Properties**:

- Typically very fast in practice
- Visits relatively few corners
- Widely used and well-understood

### Interior Point Methods

**Modern algorithm**:

1. Start inside feasible region
2. Move through the interior toward optimum
3. Approach optimal solution from inside

**Properties**:

- Better scaling for very large problems
- More predictable performance
- Used by solvers like HiGHS

### HAEO's Solver: HiGHS

**Why HiGHS?**:

- ✅ Open source (MIT license)
- ✅ State-of-the-art performance
- ✅ Actively maintained
- ✅ Python bindings via PuLP
- ✅ Handles LP, MIP, and QP

**Alternative solvers**: GLPK, CBC, Gurobi (commercial)

**Solver selection in HAEO**: Configurable, defaults to HiGHS

## Comparison with Other Optimization Approaches

### Linear Programming (LP)

**HAEO uses this**

- ✅ Very fast solving
- ✅ Guaranteed global optimum
- ✅ Handles large problems
- ❌ Requires linear formulations
- ❌ Cannot model some complex behaviors

### Mixed-Integer Programming (MIP)

**For discrete decisions**

- Use case: On/off decisions, equipment selection
- ✅ More expressive (models discrete choices)
- ❌ Much slower solving (NP-hard)
- ❌ No optimality guarantee in time limit

**HAEO decision**: LP is sufficient and much faster

### Nonlinear Programming (NLP)

**For nonlinear relationships**

- Use case: Quadratic costs, efficiency curves
- ✅ Models complex physical relationships
- ❌ No global optimum guarantee
- ❌ Can get stuck in local minima
- ❌ Slower and less reliable

**HAEO decision**: Linear approximations work well

### Model Predictive Control (MPC)

**Real-time control approach**

- Similar to HAEO's rolling horizon
- Can use LP, MIP, or NLP internally
- ✅ Adapts to changing conditions
- ✅ Industry standard for process control

**HAEO is a form of LP-based MPC**

### Heuristic Methods

**Examples**: Genetic algorithms, particle swarm, simulated annealing

- Use case: When exact optimization is too hard
- ✅ Can handle any problem type
- ❌ No optimality guarantee
- ❌ Non-deterministic results
- ❌ Much slower than LP

**HAEO decision**: LP provides provably optimal solutions, no need for heuristics

## Limitations of LP in Energy Systems

### What LP Cannot Model Directly

**1. On/off decisions** (discrete):

- Equipment startup/shutdown
- Binary choices (use equipment A or B)
- **Workaround**: Not needed for HAEO's use case

**2. Nonlinear efficiency curves**:

- Efficiency varying with power level
- Battery degradation as nonlinear function
- **Workaround**: Use average efficiency (close enough)

**3. Ramp rate limits**:

- Max change in power per time step
- Rate-of-change constraints
- **Workaround**: Can be linearized as $|P(t+1) - P(t)| \leq R_{\max}$

**4. Minimum runtime constraints**:

- Equipment must run for X hours once started
- **Workaround**: Not relevant for HAEO (continuous entities)

### When LP is Sufficient

For HAEO's application, LP works perfectly because:

- ✅ Power flows are continuous (not on/off)
- ✅ Costs are linear (or close enough)
- ✅ Efficiency is approximately constant
- ✅ No discrete equipment decisions

## Practical Considerations

### Numerical Stability

**Well-conditioned problems**:

- Variables in similar magnitude ranges
- HAEO uses kW, kWh, hours (all 0.001-1000 range)
- Avoids numerical errors

**Solver tolerance**:

- Typical: 1e-6 to 1e-9
- Solutions are accurate to practical precision
- Small numerical noise is negligible

### Infeasibility Debugging

When optimization fails (infeasible):

1. **Check load vs generation**: Can supply meet demand?
2. **Check battery limits**: Are SOC limits achievable?
3. **Check connection limits**: Are power flows physically possible?
4. **Check network connectivity**: Is everything connected?

HAEO validates network structure before optimization to catch many issues early.

### Solution Uniqueness

**LP may have multiple optimal solutions**:

- Different power flows with same total cost
- Solver returns one optimal solution
- All optimal solutions have same objective value

**Example**: Two identical batteries could split load differently while achieving same cost.

## Related Documentation

- [Objective Function](objective-function.md) - What HAEO minimizes
- [Power Balance](power-balance.md) - Equality constraints
- [Battery Modeling](battery.md) - Example entity with constraints
- [Time Horizons](time-horizons.md) - Optimization horizon and periods

## Next Steps

Now that you understand LP fundamentals, explore how HAEO applies them:

- [Objective Function](objective-function.md) - Detailed cost formulation
- [Battery Modeling](battery.md) - Complete LP formulation for batteries
- [Power Balance](power-balance.md) - How constraints ensure physical validity

[:octicons-arrow-right-24: Return to Modeling Index](index.md)
