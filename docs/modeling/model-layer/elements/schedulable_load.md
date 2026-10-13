# Schedulable Load Model

This page explains how HAEO models schedulable loads: appliances that run a fixed power profile once per window and cannot stop once started.

## Overview

A schedulable load runs one **run** of its power profile inside each scheduled window.
The optimizer chooses the period boundary the run starts at, and the whole profile must fit between that start and the window's end.
Dishwashers, washing machines, and dryers are typical: they draw a known profile for a known time, and once started they finish.

The profile is a sequence of steps, each a duration and a constant power.
A load described by one power and one run time is a one-step profile.
An appliance with distinct phases (heat, wash, dry) is a longer profile, and the formulation does not change.

Windows use the same structure as the [deferrable load](deferrable_load.md): they never overlap, and each is settled at its end boundary.
Each window must receive one run.
A missed run is priced rather than enforced, so a window that cannot fit the profile keeps the optimization feasible.

Every variable and constraint is sized by the horizon.
Windows, the profile, and a run already in progress only change parameter values and coefficients, so the problem keeps its shape across re-optimizations.

## Model formulation

The schedulable load follows the [fence post pattern](../../index.md#power-and-energy-discretization) used throughout HAEO's optimization.
Periods are indexed $t \in \{1, \ldots, T\}$, where period $t$ runs from boundary $t-1$ to boundary $t$.
Boundaries are indexed $k \in \{0, 1, \ldots, T\}$, with $\tau(k)$ the time of boundary $k$ in hours from the horizon start.

### Parameters

**Required parameters**:

- $P_j, D_j$: Power (kW) and duration (hours) of profile step $j$ - `profile_power`, `profile_duration`
- $w(t) \in \{0, 1\}$: 1 where period $t$ lies inside a window - `in_window`
- $s(k) \in \{0, 1\}$: 1 where a window starts at boundary $k$ - `window_start`
- $p_D(k) \geq 0$: Price per kWh of a run missed by the window ending at boundary $k$ (\$/kWh) - `deficit_price`

**Optional parameters**:

- $a$: How long the run in progress at the horizon start has been running (hours), or none when idle - `elapsed`
- $\sigma \in \{0, 1\}$: 1 when the window open at the horizon start already had its run start - `window_started`
- `integer_mode`: Which start weights are integer - `none`, `first` (default), or `all`
- `outbound_tags`, `inbound_tags`: As for every network element (see [Tagged Power](../../tagged-power.md))

The deficit price must be non-negative, and the model raises an error otherwise: a negative price would reward missing runs.

### Profile geometry

The profile's cumulative energy $F(x)$ after running for $x$ hours is piecewise linear, rising by $P_j D_j$ across step $j$:

$$
F(x) = \begin{cases} 0 & x \leq 0 \\ \text{linear interpolation of } \left(\sum_{i<j} D_i,\ \sum_{i<j} P_i D_i\right) & 0 < x < D \\ \sum_j P_j D_j & x \geq D \end{cases}
$$

where $D = \sum_j D_j$ is the run duration and $\bar{E} = F(D)$ is the energy of one run.

A run starting at boundary $j$ consumes this energy in period $t$:

$$
A(t, j) = F\left(\tau(t) - \tau(j)\right) - F\left(\tau(t-1) - \tau(j)\right)
$$

Runs only reach forward in time, so $A$ is lower triangular.
Each column covers a contiguous run of periods, giving the matrix its consecutive-ones structure.
A run that would pass the horizon end is cut off there; the window rules below never allow such a start unless the window itself is clamped to the horizon.

A run already in progress consumes the rest of its profile from the horizon start:

$$
C(t) = F\left(a + \tau(t)\right) - F\left(a + \tau(t-1)\right)
$$

and holds the load until $\tau_C = \max(D - a, 0)$.
Without a run in progress, $C(t) = 0$ and $\tau_C = 0$.

### Derived window structure

The carry $c(t)$ and window end mask $e(k)$ are the same as the [deferrable load's](deferrable_load.md#derived-window-structure).
Let $\epsilon(t)$ be the boundary where the window containing period $t$ ends.

A run may start at boundary $j$ when the period after it is inside a window, the profile fits before that window ends, and the committed run has finished:

$$
\alpha(j) = w(j+1) \cdot \left[\tau(j) + D \leq \tau(\epsilon(j+1))\right] \cdot \left[\tau(j) \geq \tau_C\right]
$$

A window running past the horizon end is clamped to the final boundary, so a run must fit before the horizon end.
A window that cannot fit the run books a missed run, and that relaxes as the horizon moves forward.

### Decision variables

- $x(j) \in [0, 1]$: Weight of the run starting at boundary $j \in [0, T-1]$
- $E(t) \geq 0$: Energy consumed in period $t$ (kWh)
- $N(k) \geq 0$: Runs started in the current window by boundary $k$
- $M(k) \geq 0$: Run missed by the window ending at boundary $k \geq 1$

### Constraints

#### 1. Profile

Each period's energy is what the chosen starts and the committed run consume there:

$$
E(t) - \sum_{j=0}^{t-1} A(t, j) \cdot x(j) = C(t) \quad \forall t \in [1, T]
$$

**Shadow price**: `schedulable_load_profile` is the marginal cost of energy in each period.

#### 2. Start window

Runs only start where the profile fits inside a window:

$$
x(j) \leq \alpha(j) \quad \forall j \in [0, T-1]
$$

#### 3. Run count

The window open at the horizon start counts a run it already started, and the count adds each start, resetting at window starts:

$$
N(0) = c(1) \cdot \sigma
$$

$$
N(t) = c(t) \cdot N(t-1) + x(t-1) \quad \forall t \in [1, T]
$$

#### 4. One run per window

At a window end the runs counted plus the missed run equal one, and away from window ends the missed run is zero:

$$
e(k) \cdot N(k) + M(k) = e(k) \quad \forall k \in [1, T]
$$

Since $N(k) \geq 0$, at most one run starts per window.
A window whose run already started has $N = 1$ throughout, so it takes no new run and books no miss.

### Cost contribution

Each missed run is priced per kWh of the profile at its window end:

$$
\text{Cost} = \sum_{k=1}^{T} p_D(k) \cdot \bar{E} \cdot M(k)
$$

The cost of the energy itself comes from the connection that feeds the load, so the optimizer places runs where energy is cheapest.

### Power balance

The load consumes $E(t) / \Delta t$ in each period and never produces power.

## Integer starts

The start weights $x(j)$ are continuous by default.
The consecutive-ones structure of $A$ means the linear relaxation often lands on a single start with weight 1.
Coupling constraints, such as a supply limit below the load's power or several loads sharing a connection, can make a fractional mix of starts cheaper.
A fractional plan cannot be executed: half a dishwasher run does not exist.

`integer_mode` chooses which start weights are binary:

| Mode    | Binary weights        | Effect                                                                     |
| ------- | --------------------- | -------------------------------------------------------------------------- |
| `none`  | None                  | Pure linear program; future and present starts may be fractional           |
| `first` | $x(0)$ only (default) | The decision to start now is all or nothing; future starts stay relaxed    |
| `all`   | Every $x(j)$          | Every start is all or nothing; the solve is a full mixed-integer program   |

Only the first period acts on the plan before HAEO re-optimizes, so `first` makes the actionable decision crisp at the cost of one binary variable.
Future starts stay relaxed and are re-decided as they approach the present.

### Shadow prices with integer starts

A mixed-integer solve reports no duals.
After the solve, the network fixes every integer variable at its solved value, makes it continuous, and solves the same objective again as a linear program.
The solution is unchanged and the duals become valid.
They are prices conditional on the chosen starts: a period the chosen run does not reach has no marginal start to price it.
The fixed bounds and integrality are restored before the next optimization.

## Next steps

<div class="grid cards" markdown>

- :material-dishwasher:{ .lg .middle } **Schedulable load modeling**

    ---

    How the device layer builds the profile and windows from your configuration.

    [:material-arrow-right: Schedulable load device](../../device-layer/schedulable_load.md)

- :material-clock-outline:{ .lg .middle } **Deferrable load model**

    ---

    The energy-based load that shares the window structure.

    [:material-arrow-right: Deferrable load formulation](deferrable_load.md)

- :material-cash:{ .lg .middle } **Shadow prices**

    ---

    How dual values become marginal price outputs.

    [:material-arrow-right: Shadow prices](../../shadow-prices.md)

</div>
