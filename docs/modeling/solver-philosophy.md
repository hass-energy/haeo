# Solver philosophy

HAEO uses the HiGHS solver for optimization.
This page explains the design philosophy behind solver mode selection.

## Optimization modes

HiGHS supports three optimization modes:

| Mode     | Variables   | Complexity  | Use case                               |
| -------- | ----------- | ----------- | -------------------------------------- |
| **LP**   | Continuous  | Polynomial  | Continuous decisions with linear costs |
| **MILP** | Some binary | Exponential | Discrete on/off decisions              |
| **QP**   | Continuous  | Polynomial  | Quadratic objectives                   |

### Linear programming

LP solves problems with continuous decision variables.
Simplex and interior-point algorithms find the global optimum in polynomial time.

LP is HAEO's preferred mode because:

- Guaranteed optimal solution
- Predictable solve times
- Shadow prices from duality theory
- No combinatorial explosion

### Mixed-integer linear programming

MILP allows binary (0/1) decision variables.
Branch-and-bound explores a tree of possibilities with worst-case exponential complexity.

Modern solvers use sophisticated pruning, so practical performance is often much better than worst case.
However, solve times can vary significantly depending on problem structure.

### Quadratic programming

QP allows quadratic terms in the objective function.
While still polynomial, QP is slower than LP.

**Limitation**: HiGHS cannot combine QP and MILP.
Quadratic objectives require all variables to be continuous.

## LP-first philosophy

HAEO prioritizes LP wherever possible:

1. **Prefer LP formulations**: Many problems that appear to require binary variables can be solved with continuous LP through careful constraint design
2. **Minimize integer variables**: When MILP is needed, use the minimum number of binary variables
3. **Binary decisions are local**: Make immediate decisions binary while leaving future decisions flexible

### When LP produces integer solutions

LP often produces integer solutions naturally when the constraint matrix has special structure.
Network flow problems and interval scheduling problems frequently have this property.

However, integer solutions from LP are **not guaranteed**.
Additional constraints like power limits, ramp rates, or coupling between elements can cause LP to produce fractional solutions.

### When MILP is required

Binary variables are needed when:

- LP produces fractional solutions that lack physical meaning (half a load running twice as long)
- Multiple elements compete for shared resources
- Power limits or other constraints couple decision variables

### Integer variable modes

Elements that support binary decisions typically offer three modes:

- **None**: All continuous (pure LP, fastest, may be fractional)
- **First**: Only the immediate decision is binary (fast, crisp near-term action)
- **All**: All decisions are binary (slower, guaranteed integer)

The "first" mode balances solution quality with performance: it ensures the next action is crisp while maintaining fast solve times.

## Complexity

Understanding complexity helps predict scaling behavior:

- **LP**: Polynomial in problem size.
    Doubling variables increases solve time predictably.
- **MILP**: Exponential in integer variable count.
    Each additional binary variable can double the search space.
- **QP**: Polynomial but slower than LP.

For real-time control, predictable solve times matter.
LP-first design keeps optimization responsive.

## Solver selection

HiGHS is HAEO's only supported solver, chosen for:

- Permissive MIT license
- Python wheels for Alpine Linux (Home Assistant's base OS)
- Active development and optimization

## Next steps

<div class="grid cards" markdown>

- :material-cube-outline:{ .lg .middle } **Model layer**

    ---

    See how elements contribute to the optimization problem.

    [:material-arrow-right: Model layer elements](model-layer/index.md)

- :material-currency-usd:{ .lg .middle } **Shadow prices**

    ---

    Understand the dual solution from LP optimization.

    [:material-arrow-right: Shadow prices guide](shadow-prices.md)

</div>
