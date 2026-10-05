# Deferrable Load Model

This page explains how HAEO models deferrable loads using linear programming.

## Overview

A deferrable load absorbs energy within scheduled windows, such as running an appliance or charging an EV before a trip.
The optimizer chooses when to deliver the energy, so the load moves to the cheapest periods inside each window.

Windows never overlap.
Each window has its own requirement, and each window is settled separately at its end boundary:

- **Shortfall**: The requirement the window missed, priced at the deficit price at the window's end
- **Overage**: Delivery beyond the requirement, either forbidden or priced at the overage price at the window's end

The requirement is a soft constraint.
Pricing the shortfall keeps the optimization feasible when the requirement physically cannot be met, while still making the optimizer work hard to meet it.

A single energy accumulator tracks the energy delivered in the current window.
It resets to zero at each window start, so its value at a window's end boundary is the energy that window received.
Every variable and constraint is sized by the horizon rather than by the number of windows.
Windows appearing, moving, or disappearing only change parameter values, so the problem keeps its shape across re-optimizations.

## Model formulation

The deferrable load follows the [fence post pattern](../../index.md#power-and-energy-discretization) used throughout HAEO's optimization.
Periods are indexed $t \in \{1, \ldots, T\}$, where period $t$ runs from boundary $t-1$ to boundary $t$.
Boundaries are indexed $k \in \{0, 1, \ldots, T\}$.

### Parameters

**Required parameters**:

- $w(t) \in \{0, 1\}$: 1 where period $t$ lies inside a window - `in_window`
- $s(k) \in \{0, 1\}$: 1 where a window starts at boundary $k$ - `window_start`
- $R(k)$: Requirement of the window ending at boundary $k$ (kWh) - `requirement`
- $p_D(k) \geq 0$: Price per kWh of shortfall settled at boundary $k$ (\$/kWh) - `deficit_price`
- $\Delta t$: Period duration (hours) - `period`

**Optional parameters**:

- $E_0$: Energy already delivered to the window open at the horizon start (kWh) - `initial_energy`, defaults to 0
- $p_O(k) \geq 0$: Price per kWh of overage settled at boundary $k$ (\$/kWh) - `overage_price`, defaults to none
- `outbound_tags`: Accepted like every network element, but unused because the load never produces power (see [Tagged Power](../../tagged-power.md))
- `inbound_tags`: Tags this load can consume — None means all tags

Scalar profiles and prices are broadcast to every period or boundary.
Both prices must be non-negative, and the model raises an error otherwise:
a negative price would reward booking a shortfall or overage that never happens.

Without an overage price, the requirement is a hard cap on each window's delivery.
Whether the overage variables exist is decided when the element is created.

### Derived window structure

The **carry** $c(t)$ is 1 when period $t$ continues the window of the boundary before it:

$$
c(t) = w(t) \cdot \left(1 - s(t-1)\right)
$$

A period with $c(t) = 0$ starts the accumulator from zero.

The **window end** mask $e(k)$ marks the last boundary of each window, where the window is settled:

$$
e(k) = w(k) \cdot \left(1 - w(k+1) \cdot \left(1 - s(k)\right)\right), \qquad w(T+1) = 0
$$

A window still open at the horizon end therefore settles at the final boundary $T$.
Windows that touch end to start stay separate: the second window's start resets the accumulator at the boundary the first window ends.

The **settled requirement** $\hat{R}(k)$ is the requirement at window ends:

$$
\hat{R}(k) = e(k) \cdot R(k)
$$

For the window open at the horizon start ($c(1) = 1$), the settled requirement at its end boundary $k^\ast$ is raised to at least the initial energy:

$$
\hat{R}(k^\ast) = \max\left(R(k^\ast),\ E_0\right)
$$

Telemetry can report more energy already delivered than the window requires.
That overshoot is sunk: it is not priced as overage, and it cannot make the hard cap infeasible.
When telemetry reports less than the requirement, the remainder $R(k^\ast) - E_0$ stays due at the window end.

### Decision variables

- $E(k) \geq 0$: Energy delivered in the current window by boundary $k$ (kWh)
- $d(t) \geq 0$: Energy delivered during period $t$ (kWh)
- $S(k) \geq 0$: Shortfall settled at boundary $k \geq 1$ (kWh)
- $O(k) \geq 0$: Overage settled at boundary $k \geq 1$ (kWh), only when an overage price is set

### Constraints

#### 1. Initial energy

The accumulator starts at the energy already delivered when the first period continues an open window:

$$
E(0) = c(1) \cdot E_0
$$

The initial energy never seeds a later window.

#### 2. Accumulation

The accumulator adds each period's delivery and resets at window starts:

$$
E(t) = c(t) \cdot E(t-1) + d(t) \quad \forall t \in [1, T]
$$

#### 3. Window gating

No energy is delivered outside windows:

$$
\left(1 - w(t)\right) \cdot d(t) \leq 0 \quad \forall t \in [1, T]
$$

#### 4. Requirement

Delivered energy plus shortfall covers the settled requirement at window ends:

$$
e(k) \cdot E(k) + S(k) \geq \hat{R}(k) \quad \forall k \in [1, T]
$$

The shortfall never exceeds the settled requirement, which pins it to zero away from window ends:

$$
S(k) \leq \hat{R}(k)
$$

**Shadow price**: `deferrable_load_requirement` is the marginal cost of requiring one more kWh at each window end.

#### 5. Cap

Delivery beyond the settled requirement at window ends is overage:

$$
e(k) \cdot E(k) - O(k) \leq \hat{R}(k) \quad \forall k \in [1, T]
$$

Without an overage price there is no $O(k)$ term, so each window's delivery is capped at its requirement.
With an overage price, the overage never exceeds the energy delivered at a window end, which pins it to zero elsewhere:

$$
O(k) \leq e(k) \cdot E(k)
$$

**Shadow price**: `deferrable_load_cap` is the marginal value of raising the cap at each window end.

#### 6. Power balance

The load only consumes power:

$$
P(t) = \frac{d(t)}{\Delta t} \quad \forall t \in [1, T]
$$

$P(t)$ is drawn from the network through the element power balance, like any other consuming element.

**Shadow price**: `element_power_balance` is the marginal value of power at the load terminals.

#### 7. Tag balance

The Element base class creates per-tag power balance constraints for all elements with tagged connections.
The load draws its power from `inbound_tags`.
See the [tagged power formulation](../../tagged-power.md#per-tag-balance) for details.

### Cost contribution

Each window's shortfall and overage are priced at its end boundary:

$$
\sum_{k=1}^{T} p_D(k) \cdot S(k) + \sum_{k=1}^{T} p_O(k) \cdot O(k)
$$

A deficit price above the cost of the energy makes the optimizer meet the requirement whenever it physically can.
A deficit price below the cost of the energy lets the optimizer skip delivery that is too expensive to be worth it.
Delivering early inside a window is never penalized, because a window is only settled at its end.

### Outputs

- `deferrable_load_power`: Power $P(t)$ consumed by the load (kW)
- `deferrable_load_energy_delivered`: Energy $E(k)$ delivered in the current window (kWh)
- `deferrable_load_energy_shortfall`: $e(k) \cdot \max(\hat{R}(k) - E(k), 0)$, the requirement each window missed (kWh)
- `deferrable_load_energy_overage`: $e(k) \cdot \max(E(k) - \hat{R}(k), 0)$, the delivery beyond each window's requirement (kWh)

Shortfall and overage outputs are computed from the delivered energy, so they are exact even where a price is zero.
The shadow prices named in the constraints above are also exposed as outputs.

## Physical interpretation

### Two windows

Consider two one-hour windows separated by an hour, each needing 3 kWh, with no supply available during the first:

- The first window ends with $E(1) = 0$, so $S(1) = 3$ kWh is priced at $p_D(1)$
- The second window starts from zero at boundary 2 and receives its 3 kWh by boundary 3
- The first window's miss never carries over into the second window

### Shortfall example

Consider a load that needs 8 kWh by the end of a two-hour window, supplied through a connection limited to 3 kW:

- At most 6 kWh can be delivered, so $E(2) = 6$ kWh
- The requirement constraint forces $S(2) \geq 2$ kWh
- The cost includes $2 \cdot p_D(2)$ for the missed energy

The optimization remains feasible, and the shortfall output reports exactly what was missed and when.

## Next steps

<div class="grid cards" markdown>

- :material-battery-charging:{ .lg .middle } **Battery model**

    ---

    Energy storage with SOC tracking and reserve pricing.

    [:material-arrow-right: Battery formulation](battery.md)

- :material-scale-balance:{ .lg .middle } **Shadow prices**

    ---

    Interpret the marginal values the constraints expose.

    [:material-arrow-right: Shadow prices](../../shadow-prices.md)

- :material-connection:{ .lg .middle } **Connections**

    ---

    Power flow paths between elements.

    [:material-arrow-right: Connection types](../connections/index.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code for the deferrable load model.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/core/model/elements/deferrable_load.py)

</div>
