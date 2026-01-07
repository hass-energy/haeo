# Solver Philosophy

HAEO uses the HiGHS solver which supports Linear Programming (LP), Mixed-Integer Linear Programming (MILP), and Quadratic Programming (QP).
This page explains HAEO's "LP-first" philosophy and when other solver modes are appropriate.

## Solver Capabilities

HiGHS provides three optimization modes with different characteristics:

| Mode     | Problem Type                     | Complexity               | Speed          | Use Case                                  |
| -------- | -------------------------------- | ------------------------ | -------------- | ----------------------------------------- |
| **LP**   | Linear Programming               | Polynomial               | Fastest        | Continuous decisions with linear costs    |
| **QP**   | Quadratic Programming            | Polynomial               | Slower than LP | Smooth cost curves, variance minimization |
| **MILP** | Mixed-Integer Linear Programming | Exponential (worst case) | Slowest        | Discrete decisions (on/off, scheduling)   |

### Linear Programming (LP)

LP solves problems with continuous decision variables and linear constraints.
The simplex or interior-point algorithms guarantee finding the global optimum in polynomial time.

**Typical solve times**: 0.01–1s for HAEO's problem sizes.

LP is HAEO's preferred mode because:

- Guaranteed optimal solution
- Predictable, fast solve times
- Well-understood duality theory (shadow prices)
- No combinatorial explosion

### Quadratic Programming (QP)

QP extends LP by allowing quadratic terms in the objective function (but not constraints).
While still polynomial complexity, QP is significantly slower than LP.

**Typical solve times**: 10–100× slower than equivalent LP.

QP use cases:

- Smoothing power profiles (minimize variance)
- Soft constraints with quadratic penalties
- Portfolio-style diversification

**Important limitation**: HiGHS cannot combine QP and MILP.
If any variable is integer, quadratic objectives are not supported.

### Mixed-Integer Linear Programming (MILP)

MILP allows some decision variables to be integers (typically binary 0/1).
The branch-and-bound algorithm explores a tree of possibilities, with worst-case exponential complexity.

**Typical solve times**: 1–100× slower than LP, depending on problem structure.
Worst case is exponentially slower, though good solvers use sophisticated techniques to prune the search space.

MILP use cases:

- Binary on/off decisions
- Scheduling discrete events
- Mutually exclusive choices

## HAEO's LP-First Philosophy

HAEO prioritizes LP solutions wherever mathematically possible:

1. **Prefer LP formulations**: Use clever constraint structures to achieve integer-like behavior from continuous LP
2. **Minimize integer variables**: When MILP is unavoidable, use the absolute minimum number of integer variables
3. **Document trade-offs**: Clearly explain performance implications when integer variables are introduced

### Techniques to Avoid MILP

Before introducing integer variables, consider these LP-compatible alternatives:

#### Total Unimodularity

Some constraint matrices naturally produce integer solutions from LP.
The [schedulable load](model-layer/elements/schedulable-load.md) exploits this: its consecutive-ones structure creates a totally unimodular matrix, guaranteeing integer solutions without binary variables.

#### Penalty Weights

Large penalty costs can discourage unwanted behavior without hard constraints.
For example, a high cost for negative power prevents reverse flow without a binary "direction" variable.

#### Auxiliary Slack Variables

Slack variables with appropriate costs can model soft constraints and approximate discrete behavior.

#### Mutually Dependent Constraints

Clever constraint coupling can enforce either/or behavior through the LP's structure rather than explicit binary variables.

### When MILP Is Required

Sometimes LP formulations don't capture the required behavior:

- **Coupled schedulable loads**: When multiple schedulable loads compete for limited power, the total unimodularity property breaks down.
    LP may produce fractional solutions (e.g., two loads each running at 50% for twice as long).

- **Hard scheduling constraints**: Some discrete decisions have no continuous approximation.

In these cases, HAEO uses MILP with minimal integer variables:

- **Single-variable MILP**: Mark only the first candidate as binary.
    This ensures the immediate decision is crisp while leaving future decisions flexible.
    Overhead: ~1× (essentially free).

- **Full MILP**: Mark all candidates as binary.
    Guaranteed integer solutions but ~10× overhead.

### Integer Variable Guidelines

When adding MILP to a model:

1. **Start with zero integers**: Try LP first with clever constraint structures
2. **Add one integer**: Often a single binary variable captures the essential discrete decision
3. **Document the scaling**: Integer count should grow sub-linearly with problem size
4. **Provide LP fallback**: Allow users to disable integer constraints for faster (possibly approximate) solutions

## Complexity Comparison

Understanding complexity helps predict solve time behavior:

### LP: O(n³) Polynomial

Solve time grows cubically with problem size.
Doubling the number of variables increases solve time by ~8×.
This is predictable and scales well.

### QP: O(n³) Polynomial (but slower constant)

Same polynomial complexity as LP but with a larger constant factor.
Expect 10–100× slower than equivalent LP.

### MILP: O(2^k) Exponential in Integer Count

Worst-case solve time doubles for each additional integer variable.
With k integer variables, the search space has 2^k nodes.

**Practical impact**:

| Integer Variables | Worst-Case Factor |
| ----------------- | ----------------- |
| 1                 | 2×                |
| 5                 | 32×               |
| 10                | 1,024×            |
| 20                | 1,048,576×        |

Modern MILP solvers use sophisticated pruning, so real-world performance is often much better.
But the exponential worst case means solve times can occasionally spike.

### Why LP-First Matters

HAEO runs optimization frequently (every 5 minutes or on state changes).
Consistent, fast solve times are essential for real-time control.

| Approach    | Solve Time | Predictability     |
| ----------- | ---------- | ------------------ |
| Pure LP     | 0.05 ms    | Highly predictable |
| Single MILP | 0.05 ms    | Predictable        |
| Full MILP   | 0.5 ms     | Some variation     |
| Naive MILP  | 5–500 ms   | Unpredictable      |

## HiGHS Limitations

### No MILP + QP Combination

HiGHS does not support quadratic objectives with integer variables.
If your problem requires both discrete decisions and smooth costs, you must choose:

- MILP with piecewise-linear cost approximation
- QP with continuous relaxation of discrete decisions

HAEO currently uses LP/MILP exclusively.
QP may be added for specific use cases (power smoothing) where integer variables are not needed.

### Solver Selection

HiGHS is the only solver supported by HAEO.
It was chosen for:

- **Performance**: State-of-the-art LP and MILP performance
- **Licensing**: Permissive MIT license
- **Compatibility**: Provides Python wheels for Alpine Linux (Home Assistant's base OS)
- **Active development**: Regular updates and improvements

Alternative solvers (CPLEX, Gurobi, SCIP) are not supported due to licensing restrictions or Alpine Linux compatibility issues.

## Next Steps

<div class="grid cards" markdown>

- :material-cube-outline:{ .lg .middle } **Model Layer**

    ---

    See how elements contribute to the optimization problem.

    [:material-arrow-right: Model Layer elements](model-layer/index.md)

- :material-calendar-clock:{ .lg .middle } **Schedulable Load**

    ---

    Example of LP formulation with optional MILP mode.

    [:material-arrow-right: Schedulable load model](model-layer/elements/schedulable-load.md)

- :material-currency-usd:{ .lg .middle } **Shadow Prices**

    ---

    Understand the dual solution from LP optimization.

    [:material-arrow-right: Shadow prices guide](shadow-prices.md)

</div>
