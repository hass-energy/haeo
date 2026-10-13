# Reserve Modeling

The Reserve device creates a single Reserve model element.
It has no connection of its own.
Instead it reads the planned power flows of its loads and generation and the stored energy of its batteries, which the network resolves by name.

## Model Elements Created

| Model Element | Name     | Parameters From Configuration                      |
| ------------- | -------- | -------------------------------------------------- |
| Reserve       | `{name}` | elements, storage, window, minimum, shortfall cost |

Loads and generation both become the reserve's elements.
Each counts by the net power flowing into it, so loads add to the demand and generation subtracts from it.

## Devices Created

| Device  | Name     | Created When | Purpose                                   |
| ------- | -------- | ------------ | ----------------------------------------- |
| Primary | `{name}` | Always       | Reserve inputs, requirement and shortfall |

## Formulation

The running net demand $D$ starts at zero and accumulates the elements' net power $p_e$ over each period $\Delta t_k$:

$$
D_0 = 0, \qquad D_{k+1} = D_k + \Delta t_k \sum_e p_e(k)
$$

The energy required at boundary $t$ is the extra reserve $m_t$ plus the largest rise in demand over the window $W$ that starts there:

$$
R_t = m_t + \max_{\tau \in [t,\, t+W]} \left( D(\tau) - D_t \right)
$$

Demand is linear between boundaries, so the maximum is reached at a boundary or at the window end.
The batteries hold the reserve together, each counting its stored energy $E_b$ after its discharge efficiency $\eta_b$, with a priced shortfall $s_t \ge 0$:

$$
\sum_b \eta_b E_{b,t} + s_t \ge R_t
$$

Requiring stored energy to be at least a maximum is the same as requiring it to be at least every term, so the reserve stays linear even when the demand depends on decisions the optimizer makes.

### Fixed-shape windows

Writing one row per boundary and window point would change the number of rows whenever period widths or the window change.
Instead time is cut into blocks one window long, so every window is the end of one block plus the start of the next.
Two chains of variables bound the running maximum of $D$ within each block, one from each end, and each boundary has three requirement rows: the rest of its block, the start of the next block up to the window end, and the window end itself.
Rows that do not currently apply become free rows, so new periods or a new window only rewrite coefficients.

### Cost

$$
C = \sum_{t=1}^{n} c_t \, s_t \, \Delta t_{t-1}
$$

where $c_t$ is the shortfall cost in \$/kWh/h.

## Parameter mapping

| User Configuration | Model Field | Notes                                                          |
| ------------------ | ----------- | -------------------------------------------------------------- |
| Loads, generation  | `elements`  | Net power into each element counts as demand                   |
| Batteries          | `storage`   | Each battery's single discharge connection sets its efficiency |
| Outage length      | `window`    | Hours                                                          |
| Extra reserve      | `minimum`   | kWh at each boundary                                           |
| Shortfall cost     | `price`     | \$/kWh/h                                                       |

## Next steps

<div class="grid cards" markdown>

- :material-shield-check:{ .lg .middle } **Configure a reserve**

    ---

    Set up a reserve in Home Assistant.

    [:material-arrow-right: Reserve configuration](../../user-guide/elements/reserve.md)

- :material-battery:{ .lg .middle } **Battery modeling**

    ---

    See how batteries store the energy the reserve counts.

    [:material-arrow-right: Battery modeling](battery.md)

</div>
