# Deferrable Load Model

This page explains how HAEO models deferrable loads using linear programming.

## Overview

A deferrable load receives energy within scheduled events, such as running an appliance or charging an EV before a trip.
The optimizer chooses when to deliver the energy, so the load moves to the cheapest periods inside each event.

Each event has its own requirement, start, and end.
Overlapping events share one window, and a single energy accumulator tracks the energy delivered since the window started.
Inside the window the accumulator must stay within a band:

- **Lower edge**: the energy due, the requirements of the events that have ended
- **Upper edge**: the energy started, the requirements of the events that have begun

Falling below the band is **shortfall**, priced at the deficit price where the event is missed.
Rising above it is **overage**, priced at the overage price where its window ends.
Neither is ever forbidden.
Pricing the shortfall keeps the optimization feasible when a requirement physically cannot be met, while still making the optimizer work hard to meet it.
Pricing the overage keeps it feasible when the device has already run past its requirement, whether by its own cycle or by someone running it.

The band keeps each event's energy inside its own time.
Energy delivered before an event starts lies above the band, so it never counts toward that event, and each event is due by its own end, not by the end of the window.

Every variable and constraint is sized by the horizon rather than by the number of events.
Events appearing, moving, or disappearing only change parameter values, so the problem keeps its shape across re-optimizations.

## Model formulation

The deferrable load follows the [fence post pattern](../../index.md#power-and-energy-discretization) used throughout HAEO's optimization.
Periods are indexed $t \in \{1, \ldots, T\}$, where period $t$ runs from boundary $t-1$ to boundary $t$.
Boundaries are indexed $k \in \{0, 1, \ldots, T\}$.

### Parameters

**Required parameters**:

- $w(t) \in \{0, 1\}$: 1 where period $t$ lies inside a window - `in_window`
- $s(k) \in \{0, 1\}$: 1 where a window starts at boundary $k$ - `window_start`
- $o(k)$: Requirements of the events starting at boundary $k$ (kWh) - `opened`
- $u(k)$: Requirements of the events ending at boundary $k$ (kWh) - `due`
- $p_D(k) \geq 0$: Price per kWh of shortfall for events due at boundary $k$ (\$/kWh) - `deficit_price`
- $p_O(k) \geq 0$: Price per kWh of overage in a window ending at boundary $k$ (\$/kWh) - `overage_price`
- $\Delta t$: Period duration (hours) - `period`

**Optional parameters**:

- $E_0$: Energy already delivered to the window open at the horizon start (kWh) - `initial_energy`, defaults to 0
- `inbound_tags`: Tags this load can consume — None means all tags (see [Tagged Power](../../tagged-power.md))

Window profiles and prices are arrays, one value per period for $w$ and one per boundary for the rest.
An event already open at the horizon start opens at boundary 0.
An event running past the horizon end is clamped to the horizon and due at the final boundary $T$; the horizon normally reaches far enough that this rarely matters, and its remaining energy is planned again as the horizon moves forward.
The requirements, initial energy, and prices are never negative: the loaders enforce this before the model sees them, since a negative price would reward booking a shortfall or overage that never happens.

### Derived window structure

The **carry** $c(t)$ is 1 when period $t$ continues the window of the boundary before it:

$$
c(t) = w(t) \cdot \left(1 - s(t-1)\right)
$$

A period with $c(t) = 0$ starts the window's totals from zero.
Windows that touch end to start stay separate: the second window's start resets them at the boundary the first window ends.

The band's edges are running totals within each window, reset wherever $c(t) = 0$:

$$
\begin{aligned}
C(k) &= c(k) \cdot C(k-1) + w(k) \cdot o(k-1) && \text{energy started by boundary } k \\
D(k) &= c(k) \cdot D(k-1) + w(k) \cdot u(k) && \text{energy due by boundary } k
\end{aligned}
$$

with $C(0) = D(0) = 0$.

The **window end** mask $e(k)$ marks the last boundary of each window:

$$
e(k) = w(k) \cdot \left(1 - c(k+1)\right), \qquad c(T+1) = 0
$$

### Decision variables

- $E(k) \geq 0$: Energy delivered in the current window by boundary $k$ (kWh)
- $S(k) \geq 0$: Energy due but not delivered by boundary $k \geq 1$ (kWh)
- $O(k) \geq 0$: Energy delivered beyond what has started by boundary $k \geq 1$ (kWh)

### Constraints

#### 1. Initial energy

The accumulator starts at the energy already delivered when the first period continues an open window:

$$
E(0) = c(1) \cdot E_0
$$

The initial energy never seeds a later window.
An overshoot it reports is overage like any other: a fixed cost that changes no decision.

#### 2. Delivery

The energy delivered during period $t$ is the accumulator's step, which restarts at window starts:

$$
d(t) = E(t) - c(t) \cdot E(t-1)
$$

It is never negative, so energy is never taken back out:

$$
d(t) \geq 0 \quad \forall t \in [1, T]
$$

#### 3. Window gating

No energy is delivered outside windows:

$$
\left(1 - w(t)\right) \cdot d(t) \leq 0 \quad \forall t \in [1, T]
$$

#### 4. Band

Delivered energy, less overage, plus shortfall reaches the energy due, and delivered energy, less overage, stays within the energy started:

$$
D(k) \leq E(k) - O(k) + S(k), \qquad E(k) - O(k) \leq C(k) \quad \forall k \in [1, T]
$$

The overage never exceeds the energy delivered, which keeps it bounded where it is unpriced:

$$
O(k) \leq E(k)
$$

**Shadow price**: `deferrable_load_requirement` is the marginal cost of requiring one more kWh by each boundary.

#### 5. Kept slack

Within a window, shortfall and overage never shrink:

$$
S(k) \geq c(k) \cdot S(k-1), \qquad O(k) \geq c(k) \cdot O(k-1) \quad \forall k \in [2, T]
$$

A missed deadline therefore stays missed, so energy arriving after an event ends cannot make it up, and overage, once booked, never counts toward a later event.

Shortfall only grows where an event is due, by at most its requirement:

$$
S(k) - c(k) \cdot S(k-1) \leq w(k) \cdot u(k) \quad \forall k \in [1, T]
$$

A boundary where nothing is due can then hold no shortfall for a later event's miss to hide behind at a cheaper price.

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
Its config declares `is_source=false` and `is_sink=true`, so policies can deliver power to the load but never draw from it.
See the [tagged power formulation](../../tagged-power.md#per-tag-balance) for details.

### Cost contribution

Shortfall is priced as it grows, at the boundary where its event is due, and each window's overage is priced once, at its end:

$$
\sum_{k=1}^{T} p_D(k) \cdot \left(S(k) - c(k) \cdot S(k-1)\right) + \sum_{k=1}^{T} e(k) \cdot p_O(k) \cdot O(k)
$$

with $S(0) = 0$.
Overage never shrinks within a window, so its value at the window's end is the window's total overage; pricing it there means booking it at an earlier, cheaper boundary gains nothing.

A deficit price above the cost of the energy makes the optimizer meet each event whenever it physically can.
A deficit price below the cost of the energy lets the optimizer skip delivery that is too expensive to be worth it.
Delivering early within an event is never penalized, because an event is only due at its end.

### Outputs

- `deferrable_load_power`: Power $P(t)$ consumed by the load (kW)
- `deferrable_load_energy_delivered`: Energy $E(k)$ delivered in the current window (kWh)
- `deferrable_load_energy_shortfall`: $S(k) - c(k) \cdot S(k-1)$, the energy missed at each boundary (kWh)
- `deferrable_load_energy_overage`: $O(k) - c(k) \cdot O(k-1)$, the energy delivered beyond what has started, at the boundary where it arises (kWh)

The shadow prices named in the constraints above are also exposed as outputs.

### Nested events

The band is exact when events do not nest, that is when an event that starts later also ends later, as staggered and back-to-back events do.
An event nested inside a longer one is still due its energy by its own end, but the band only counts energy from the window's start, so energy delivered for the longer event before the nested one starts can satisfy it.
Keeping a nested event's energy inside its own time needs a check over its own start and end.

## Physical interpretation

### Overlapping events

Consider two 2-hour events overlapping by an hour, A over periods 1-2 and B over periods 2-3, each needing 2 kWh, with the first hour cheapest:

- $C(1) = 2$, so the first hour can deliver at most A's 2 kWh; anything more is overage and never counts toward B
- $D(2) = 2$, so A must be complete by its own end at boundary 2
- $D(3) = 4$, so B's 2 kWh lands in periods 2-3, inside its own time

### Missed deadline

With no supply until period 3 in the same example:

- A ends with nothing delivered, so $S(2) = 2$ kWh is priced at $p_D(2)$
- Period 3 delivers B's 2 kWh; $S(3) \geq S(2)$, so energy arriving after A ended cannot make up A's shortfall
- A's miss is priced once, at the boundary where A ended

## Next steps

<div class="grid cards" markdown>

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
