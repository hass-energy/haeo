# Buffer model

The Buffer model element keeps energy or empty space in a group of batteries over a window of time.
A **reserve** keeps the energy the batteries need to cover the net demand of a group of elements through a window, such as a grid outage.
**Headroom** is the mirror image: the empty space the batteries need to absorb the net surplus of a group of elements over the window.

## Overview

Buffer is a flow reader.
It produces and consumes nothing and has no connections of its own.
Instead it reads the planned power of its loads, the power limits on the connections out of its generation, and the stored energy of its batteries.

The requirement at each boundary is the largest rise in the elements' running net demand (or surplus, for headroom) within the window that starts there.
Any shortfall is priced rather than forbidden, so a buffer the batteries cannot hold never makes the optimization infeasible.

The [buffer device modeling](../../device-layer/buffer.md) page has the full formulation, including the base each battery is measured from, the efficiency scaling between stored and network-side energy, and the outputs.

## Model formulation

### Decision variables

For each boundary $t \in \{0, 1, \ldots, T\}$:

| Variable            | Domain                | Description                                                         |
| ------------------- | --------------------- | ------------------------------------------------------------------- |
| $D(t)$              | $\mathbb{R}$          | Running net demand (or surplus, for headroom) of the elements (kWh) |
| $M^{\text{suf}}(t)$ | $\mathbb{R}$          | Peak running demand from $t$ to the end of its block (kWh)          |
| $M^{\text{pre}}(t)$ | $\mathbb{R}$          | Peak running demand from the start of its block to $t$ (kWh)        |
| $s(t)$              | $\mathbb{R}_{\geq 0}$ | Stored energy the batteries fall short of the buffer (kWh)          |

### Parameters

| Parameter    | Description                                                                          |
| ------------ | ------------------------------------------------------------------------------------ |
| `kind`       | `reserve` or `headroom`                                                              |
| `loads`      | Elements whose planned consumption the buffer covers                                 |
| `generation` | Elements whose possible production the buffer covers                                 |
| `storage`    | Batteries that hold the buffer                                                       |
| `window`     | Window length (hours)                                                                |
| `level`      | Share of capacity the buffer is measured from, or unset to use the min or max charge |
| `price`      | Shortfall cost per stored kWh per hour (\$/kWh/h)                                    |

`window`, `level`, and `price` are tracked parameters, so changing them rebuilds only the constraints and costs that use them.

### Constraints

#### Demand balance

The running demand starts at zero and accumulates the elements' net power over each period:

$$
D(0) = 0, \qquad D(t+1) = D(t) + \sigma \, \Delta t_t \, P_{\text{net}}(t)
$$

where $\sigma$ is $1$ for a reserve and $-1$ for headroom.

#### Block peaks

Time is cut into blocks one window long, so every window is the end of one block plus the start of the next.
$M^{\text{suf}}$ and $M^{\text{pre}}$ bound the running demand within each block from either end.
Links between boundaries in different blocks have no lower bound, so they become free rows.

#### Requirement

At each boundary the energy the batteries hold past their base, plus the scaled shortfall, must cover the peak demand within the window.
There are three rows per boundary: the rest of its own block, the start of the next block up to the window end, and the interpolated window end when it falls inside a period.
Rows that do not apply become free rows, so the problem keeps its shape when the periods or the window change.

### Cost contribution

The shortfall is charged per stored kWh per hour.
Each boundary is held for the period before it, and the first boundary for the first period:

$$
C = c_0 \, s(0) \, \Delta t_0 + \sum_{t=1}^{T} c_{t-1} \, s(t) \, \Delta t_{t-1}
$$

### Outputs

| Output                    | Description                                                           |
| ------------------------- | --------------------------------------------------------------------- |
| `buffer_energy_required`  | Stored energy to hold (or keep free) past the base at each boundary   |
| `buffer_energy_available` | Stored energy held (or kept free) past the base at each boundary      |
| `buffer_energy_shortfall` | Stored energy the batteries fall short of the buffer at each boundary |
| `buffer_state_of_charge`  | Combined state of charge the batteries should stay above (or below)   |

## Next steps

<div class="grid cards" markdown>

- :material-shield-check:{ .lg .middle } **Buffer modeling**

    ---

    The full formulation and how configuration maps to it.

    [:material-arrow-right: Buffer device modeling](../../device-layer/buffer.md)

- :material-battery-charging:{ .lg .middle } **Battery model**

    ---

    The stored energy and limits a buffer reads.

    [:material-arrow-right: Battery formulation](battery.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code for the buffer model.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/core/model/elements/buffer.py)

</div>
