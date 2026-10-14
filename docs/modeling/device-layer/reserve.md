# Reserve and Headroom Modeling

The Reserve and Headroom devices each create a single Reserve model element, with its kind set to `reserve` or `headroom`.
Neither has a connection of its own.
Instead the element reads the planned power of its loads, the forecast power of its generation, and the stored energy of its batteries, which the network resolves by name.

## Model Elements Created

| Model Element | Name     | Parameters From Configuration                                     |
| ------------- | -------- | ----------------------------------------------------------------- |
| Reserve       | `{name}` | kind, loads, generation, storage, window, minimum, shortfall cost |

Loads count by the net power flowing into them, so a load whose timing the optimizer chooses moves the requirement with its schedule.
Generation counts by the limit on the power leaving it, which is its forecast, so curtailing it in the plan cannot shrink a headroom that exists to make room for it.

## Devices Created

| Device  | Name     | Created When | Purpose                           |
| ------- | -------- | ------------ | --------------------------------- |
| Primary | `{name}` | Always       | Inputs, requirement and shortfall |

## Formulation

The running net demand $D$ starts at zero and accumulates the loads' planned power $p_l$ less the generation's forecast power $g_j$ over each period $\Delta t_k$.
For headroom the sign is flipped, so $D$ tracks the running net surplus instead:

$$
D_0 = 0, \qquad D_{k+1} = D_k + \sigma \, \Delta t_k \left( \sum_l p_l(k) - \sum_j g_j(k) \right), \qquad \sigma = \begin{cases} 1 & \text{reserve} \\ -1 & \text{headroom} \end{cases}
$$

The requirement at boundary $t$ is the extra amount $m_t$ plus the largest rise in $D$ over the window $W$ that starts there:

$$
R_t = m_t + \max_{\tau \in [t,\, t+W]} \left( D(\tau) - D_t \right)
$$

$D$ is linear between boundaries, so the maximum is reached at a boundary or at the window end.
The batteries meet the requirement together, with a priced shortfall $s_t \ge 0$.
A reserve counts the stored energy $E_b$ each battery can deliver after its discharge efficiency $\eta^{d}_b$, and headroom counts the empty space each can fill before its charge efficiency $\eta^{c}_b$, where $C_b$ is its usable capacity:

$$
\text{reserve:} \quad \sum_b \eta^{d}_b E_{b,t} + s_t \ge R_t
\qquad\qquad
\text{headroom:} \quad \sum_b \frac{C_{b,t} - E_{b,t}}{\eta^{c}_b} + s_t \ge R_t
$$

Requiring the batteries to provide at least a maximum is the same as requiring them to provide at least every term, so the requirement stays linear even when the loads depend on decisions the optimizer makes.

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

| User Configuration       | Model Field  | Notes                                                                                         |
| ------------------------ | ------------ | --------------------------------------------------------------------------------------------- |
| Element type             | `kind`       | `reserve` or `headroom`                                                                       |
| Loads                    | `loads`      | Planned net power into each load                                                              |
| Generation               | `generation` | Forecast power, the limit on each generator's outgoing connection                             |
| Batteries                | `storage`    | Each battery's single discharge (reserve) or charge (headroom) connection sets its efficiency |
| Outage length/Look-ahead | `window`     | Hours                                                                                         |
| Extra reserve/headroom   | `minimum`    | kWh at each boundary                                                                          |
| Shortfall cost           | `price`      | \$/kWh/h                                                                                      |

## State of charge line

The reserve and headroom state of charge sensors turn the requirement into a combined state of charge for the forecast card.
A reserve adds the requirement, stored at the batteries' discharge efficiency, to their lowest allowed charge.
Headroom takes the requirement, stored at their charge efficiency, away from their highest allowed charge.
Efficiencies are weighted by capacity, so the line is exact for one battery and for batteries with the same efficiency.

## Next steps

<div class="grid cards" markdown>

- :material-shield-check:{ .lg .middle } **Configure a reserve**

    ---

    Set up a reserve in Home Assistant.

    [:material-arrow-right: Reserve configuration](../../user-guide/elements/reserve.md)

- :material-format-vertical-align-top:{ .lg .middle } **Configure headroom**

    ---

    Set up headroom in Home Assistant.

    [:material-arrow-right: Headroom configuration](../../user-guide/elements/headroom.md)

- :material-battery:{ .lg .middle } **Battery modeling**

    ---

    See how batteries store the energy and space these count.

    [:material-arrow-right: Battery modeling](battery.md)

</div>
