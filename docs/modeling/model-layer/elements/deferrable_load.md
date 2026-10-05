# Deferrable Load Model

This page explains how HAEO models deferrable loads using linear programming.

## Overview

A deferrable load absorbs a required amount of energy within scheduled windows, such as charging an EV before a trip.
The optimizer chooses when to absorb the energy, so the load moves to the cheapest periods inside its windows.

The model tracks cumulative absorbed energy against two boundary-aligned profiles:

- **Capacity**: The maximum cumulative energy absorbable by each boundary, which opens as scheduled windows begin
- **Requirement**: The cumulative energy that should have been absorbed by each boundary, which falls due as scheduled windows end

The requirement is a soft constraint.
A shortfall is priced at the boundary where the missed requirement falls due, and absorption beyond the final requirement is priced once at the end of the horizon.
This keeps the optimization feasible when the requirement physically cannot be met, while still making the optimizer work hard to meet it.

## Model formulation

The deferrable load follows the [fence post pattern](../../index.md#power-and-energy-discretization) used throughout HAEO's optimization.
Power has $T$ values indexed as $t \in \{0, 1, \ldots, T-1\}$.
Energy and deficit are instantaneous values at time boundaries and have $T+1$ values indexed as $t \in \{0, 1, \ldots, T\}$.

### Decision variables

- $E(t) \geq 0$: Cumulative energy absorbed by boundary $t$ (kWh)
- $D(t) \geq 0$: Locked-in shortfall against the requirement at boundary $t$ (kWh)
- $O \geq 0$: Absorption beyond the final requirement (kWh), a single variable for the whole horizon

**Initial conditions**:

- $E(0) = E_0$: Energy already absorbed before the horizon
- $D(0) = 0$: No shortfall before the horizon

### Parameters

**Required parameters**:

- $C(t)$: Cumulative capacity at boundary $t$ (kWh) - `capacity`
- $R(t)$: Cumulative requirement at boundary $t$ (kWh) - `required`
- $p_D(t) \geq 0$: Price per kWh of shortfall falling due at boundary $t$ (\$/kWh) - `deficit_price`
- $\Delta t$: Time step duration (hours) - `period`

**Optional parameters**:

- $E_0$: Energy already absorbed (kWh) - `initial_energy`, defaults to 0
- $p_O \geq 0$: Price per kWh of absorption beyond the final requirement (\$/kWh) - `overage_price`, defaults to 0
- `outbound_tags`: Accepted like every network element, but unused because the load never produces power (see [Tagged Power](../../tagged-power.md))
- `inbound_tags`: Tags this load can consume — None means all tags

Scalar profiles and prices are broadcast to every boundary.
Both prices must be non-negative, and the model raises an error otherwise:
a negative price would reward booking a shortfall or overshoot that never happens.

### Constraints

#### 1. Energy flow

Cumulative absorbed energy can only increase:

$$
E(t+1) \geq E(t) \quad \forall t \in [0, T-1]
$$

**Shadow price**: `deferrable_load_energy_flow` is the marginal value of relaxing monotonic absorption.

#### 2. Capacity

Absorbed energy cannot exceed the opened capacity:

$$
E(t) \leq \max\left(C(t),\ E_0\right) \quad \forall t \in [1, T]
$$

Live telemetry can report more energy already absorbed than the schedule planned for, such as an EV that drove further than forecast.
The effective capacity never sits below $E_0$, so stale telemetry cannot make the optimization infeasible.

**Shadow price**: `deferrable_load_capacity` is the marginal value of additional capacity at each boundary.

#### 3. Requirement

Absorbed energy plus deficit covers the requirement:

$$
E(t) + D(t) \geq R(t) \quad \forall t \in [1, T]
$$

**Shadow price**: `deferrable_load_requirement` is the marginal cost of requiring one more kWh by each boundary.

#### 4. Locked-in deficit

The deficit never shrinks, so a shortfall at a deadline stays priced even if absorption later catches up:

$$
D(t) \geq D(t-1) \quad \forall t \in [1, T]
$$

#### 5. Due-capped deficit

Each deficit increment is limited to the requirement newly falling due at that boundary.
The due profile $U(t)$ is the requirement not already covered by the initial energy, made non-decreasing:

$$
U(t) = \max_{1 \leq \tau \leq t} \max\left(R(\tau) - E_0,\ 0\right), \qquad U(0) = 0
$$

$$
D(t) - D(t-1) \leq U(t) - U(t-1) \quad \forall t \in [1, T]
$$

The increments of $U$ sum to at least the worst possible shortfall at every boundary, so the requirement constraint always stays feasible.
A shortfall can only be booked, and priced, at a boundary where requirement actually falls due.

#### 6. Overage

Overage covers absorption beyond the final requirement, measured from a baseline $B$:

$$
B = \max\left(R(T),\ E_0\right)
$$

$$
O \geq E(T) - B
$$

Energy already absorbed before the horizon is not overage: an overshoot reported by live telemetry is a fact, not a decision to price.

Overage is also limited to the room absorbable past the requirement, which keeps it bounded when it is unpriced:

$$
O \leq \max\left(\max\left(C(T),\ E_0\right) - B,\ 0\right)
$$

#### 7. Power balance

The load only consumes power:

$$
P(t) = \frac{E(t+1) - E(t)}{\Delta t} \quad \forall t \in [0, T-1]
$$

$P(t)$ is drawn from the network through the element power balance, like any other consuming element.

**Shadow price**: `element_power_balance` is the marginal value of power at the load terminals.

#### 8. Tag balance

The Element base class creates per-tag power balance constraints for all elements with tagged connections.
The load draws its power from `inbound_tags`.
See the [tagged power formulation](../../tagged-power.md#per-tag-balance) for details.

### Cost contribution

Each deficit increment is priced at the boundary where it falls due, and overage is priced once:

$$
\sum_{t=1}^{T} p_D(t) \cdot \left(D(t) - D(t-1)\right) + p_O \cdot O
$$

With a scalar deficit price, the deficit term telescopes to $p_D \cdot D(T)$.

A deficit price above the cost of the energy makes the optimizer meet the requirement whenever it physically can.
A deficit price below the cost of the energy lets the optimizer skip absorption that is too expensive to be worth it.

### Outputs

- `deferrable_load_power`: Power $P(t)$ consumed to absorb energy (kW)
- `deferrable_load_energy_absorbed`: Cumulative absorbed energy $E(t)$ (kWh)
- `deferrable_load_energy_deficit`: Locked-in shortfall $D(t)$ (kWh)

The shadow prices named in the constraints above are also exposed as outputs.

## Physical interpretation

### Shortfall example

Consider a load that needs 8 kWh by the end of a two-hour window, supplied through a connection limited to 3 kW:

- At most 6 kWh can be absorbed, so $E(2) = 6$ kWh
- The requirement constraint forces $D(2) \geq 2$ kWh
- The due profile allows the full 8 kWh to fall due at $t = 2$, so the 2 kWh increment is booked there
- The cost includes $2 \cdot p_D(2)$ for the missed energy

The optimization remains feasible, and the deficit output reports exactly what was missed and when.

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
