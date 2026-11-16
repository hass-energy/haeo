# Level segments

Level segments set or cap a connection's flow by the difference in level between its endpoints.
A level is a quantity that drives flow between two elements, such as a temperature driving heat through a wall.
The conduction segment fixes the flow and the level limit segment caps it.

## Levels

Each element a level segment joins exposes one level per period, read at the end of the period.

| Element | Level                                                          |
| ------- | -------------------------------------------------------------- |
| Battery | $L(t) = L_0 + E(t) / c$, from its stored energy $E$            |
| Node    | A forecast $L(t)$, such as the temperature of a tank's housing |

A battery's level offset $L_0$ defaults to 0 and its energy per level $c$ to 1,
so its level is its stored energy in kWh unless the device layer sets them.
A thermal mass is an unbounded battery with $L_0$ at its current temperature and $c$ its heat capacity, so its level is its temperature.
A node's level defaults to 0.

A segment may be given a source or target level, a forecast that replaces that end's own level.
A coil feeding a tap uses the cold inlet temperature this way, so the tap can be a plain junction,
and a fresh-air damper uses the outdoor temperature.

A level segment joining an element without a level is a configuration error.

## Model formulation

### Parameters

| Parameter | Description                                            | Units             |
| --------- | ------------------------------------------------------ | ----------------- |
| $G(t)$    | Conductance: power per unit of level difference        | kW per level unit |
| $L_s(t)$  | Level of the source at the end of period $t$           | level unit        |
| $L_d(t)$  | Level of the target (destination) at the end of period | level unit        |

### Conduction

The conduction segment fixes the flow at the conductance times the level difference:

$$
P^{\text{in}}(t) \cdot \Delta t = G(t) \cdot \left(L_s(t) - L_d(t)\right) \cdot \Delta t
$$

The flow runs from source to target when the source is higher and from target to source when it is lower,
so a connection holding a conduction segment has flow variables in $\mathbb{R}$ rather than $\mathbb{R}_{\geq 0}$.
The plan has no control over it.

### Level limit

The level limit segment caps the flow at the conductance times the level difference, with priced slack $s(t) \geq 0$:

$$
P^{\text{in}}(t) \cdot \Delta t \leq \left(G(t) \cdot \left(L_s(t) - L_d(t)\right) + s(t)\right) \cdot \Delta t
$$

The flow stays one-way and the plan chooses it below the cap.
When the source falls to the target's level the cap reaches zero.

Without the slack, a one-way flow under a cap below zero would force the source's level to stay above the target's,
so a tank colder than the water its coil heats would make the plan infeasible.
The slack costs its violation price per kWh, 100 \$/kWh by default, far above any energy price,
so the cap holds unless the levels already sit the wrong way round.

### Controlled conductance

A flow the plan controls by opening something, such as a damper letting in outdoor air,
moves $d \cdot G \cdot (L_s - L_d)$ for an opening $d \in [0, 1]$.
That is a product of two decisions, the opening and the level, so it cannot be a constraint itself.
The level limit expresses it exactly once the plan decides the flow rather than the opening:
every flow between zero and the cap is some opening, recovered after the solve as $P^{\text{in}} / (G \cdot (L_s - L_d))$.

What remains is the flow's direction, which the levels decide.
It is chosen before the optimization, from forecasts, by the conductance:
$G(t)$ in periods where the direction is certain, such as outdoor air below a room's comfort minimum for cooling,
and 0 elsewhere, which caps the flow at zero and constrains no level.

Both constraints are written in energy, so their shadow prices are in \$/kWh.

## Stability over long periods

The flow reads the level at the end of each period, not the start.
For a store of heat with capacity $C$ losing heat to surroundings at level $L_a$, one period gives

$$
L(t) = \frac{L(t-1) + \frac{G \Delta t}{C} L_a}{1 + \frac{G \Delta t}{C}}
$$

which moves toward $L_a$ and never passes it, however long the period.
Reading the start of the period instead would give $L(t) = L(t-1) - \frac{G \Delta t}{C}(L(t-1) - L_a)$,
which overshoots the surroundings and oscillates once $\Delta t$ exceeds the time constant $C / G$.
HAEO's later periods are long, so end-of-period levels keep the plan physical across the whole horizon.
For periods much shorter than $C / G$ both approach the exact exponential decay.

## Physical interpretation

| Use                                    | Segment     | Source and target                      |
| -------------------------------------- | ----------- | -------------------------------------- |
| Heat lost through a wall or insulation | Conduction  | A thermal mass and a node at ambient   |
| Heat passing between two rooms         | Conduction  | Two thermal masses                     |
| A battery's self-discharge             | Conduction  | A battery and a node at level 0        |
| A heat exchanger coil                  | Level limit | A tank and a tap, at the inlet's level |
| A fresh-air damper                     | Level limit | A room and outdoors, at the forecast   |

## Next steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connection model**

    ---

    Segment-based connection formulation.

    [:material-arrow-right: Connection formulation](../connections/connection.md)

- :material-layers:{ .lg .middle } **Segments**

    ---

    How segments compose into a connection.

    [:material-arrow-right: Segments overview](index.md)

- :material-thermometer:{ .lg .middle } **Thermal mass**

    ---

    How a thermal mass builds a store, its surroundings, and the conduction between them.

    [:material-arrow-right: Thermal mass modeling](../../device-layer/thermal_mass.md)

</div>
