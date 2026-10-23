# Buffer modeling

The Buffer device creates a single Buffer model element, with its kind set to `reserve` or `headroom`.
It has no connection of its own.
Instead the element reads the planned power and unmet energy of its loads, the forecast power of its generation, and the stored energy of its batteries, which the network resolves by name.

## Model elements created

| Model element | Name     | Parameters from configuration                                   |
| ------------- | -------- | --------------------------------------------------------------- |
| Buffer        | `{name}` | kind, loads, generation, storage, window, level, shortfall cost |

Loads count by the net power flowing into them, so a load whose timing the optimizer chooses moves the requirement with its schedule.
A load that can fall short, such as a deferrable load or an EV's trip load, also counts the energy the plan leaves unmet, in the period where it falls due.
Its need then counts whether or not the plan meets it, so leaving a load short cannot shrink a reserve that exists to cover it.
Generation counts by the power limits on the connections out of it, the most the network lets it produce, which is its forecast.
Curtailing it in the plan cannot shrink a headroom that exists to make room for it.

Each battery's efficiency comes from the connections it discharges through for a reserve, or charges through for headroom.
It converts between the energy the elements need at the network and the energy stored in the battery.
With several such connections the lowest efficiency counts, so the buffer never relies on more than the worst path gives, and a battery with none counts without losses.

The buffer reads all of this from the elements and their connections, so any element that consumes, produces, or stores power can take part, whatever kind of device it is.

## Devices created

| Device  | Name     | Created when | Purpose                           |
| ------- | -------- | ------------ | --------------------------------- |
| Primary | `{name}` | Always       | Inputs, requirement and shortfall |

## Formulation

### Running demand

The running net demand $D$ starts at zero and accumulates the loads' planned power $p_l$ and unmet energy $u_l$ less the generation's forecast power $g_j$ over each period $\Delta t_k$.
For headroom the sign is flipped, so $D$ tracks the running net surplus instead:

$$
D_0 = 0, \qquad D_{k+1} = D_k + \sigma \, \Delta t_k \left( \sum_l \left( p_l(k) + \frac{u_l(k)}{\Delta t_k} \right) - \sum_j g_j(k) \right), \qquad \sigma = \begin{cases} 1 & \text{reserve} \\ -1 & \text{headroom} \end{cases}
$$

The network-side requirement at boundary $t$ is the largest rise in $D$ over the window $W$ that starts there:

$$
R_t = \max_{\tau \in [t,\, t+W]} D(\tau) - D_t
$$

$D$ is linear between boundaries, so the maximum is reached at a boundary or at the window end.
When the window ends inside a period, $D$ at the window end is interpolated between the last boundary inside the window and the next one.

### Base

Each battery $b$ is measured from a base $B_{b,t}$, set by the level $\ell_t$ as a share of its capacity $Q_b$ and never past its own min charge $E^{\min}_b$ or max charge $E^{\max}_b$:

$$
\text{reserve:} \quad B_{b,t} = \max\left(E^{\min}_{b,t},\, \ell_t Q_{b,t}\right)
\qquad\qquad
\text{headroom:} \quad B_{b,t} = \min\left(E^{\max}_{b,t},\, \ell_t Q_{b,t}\right)
$$

With no level, the base is the min charge for a reserve, or zero when that is unset, and the max charge for headroom, or the capacity when that is unset.

### Requirement

Each stored kWh is worth $f_b$ kWh at the network: the discharge efficiency $\eta^{d}_b$ for a reserve, and $1/\eta^{c}_b$ for headroom, since filling a kWh of space takes more than a kWh from the network.
The batteries meet the requirement together, with a shortfall $s_t \ge 0$ measured in stored kWh:

$$
\text{reserve:} \quad \sum_b f_b \left(E_{b,t} - B_{b,t}\right) + \bar{f}_t \, s_t \ge R_t
\qquad\qquad
\text{headroom:} \quad \sum_b f_b \left(B_{b,t} - E_{b,t}\right) + \bar{f}_t \, s_t \ge R_t
$$

where $\bar{f}_t = \sum_b f_b Q_b / \sum_b Q_b$ is the capacity-weighted network worth of a stored kWh.
Scaling the shortfall this way prices it per kWh stored in the batteries, exactly for one battery and for batteries with the same efficiency.

Requiring the batteries to provide at least a maximum is the same as requiring them to provide at least every term, so the requirement stays linear even when the loads depend on decisions the optimizer makes.

The requirement holds at every boundary, the first included.
The batteries' charge at the first boundary is fixed, but the window after it covers the first periods' planned flows, so a load scheduled into the first period counts like any other.

### Fixed-shape windows

Writing one row per boundary and window point would change the number of rows whenever period widths or the window change.
Instead time is cut into blocks one window long, so every window is the end of one block plus the start of the next.
Two chains of variables bound the running maximum of $D$ within each block, one from each end, and each boundary has three requirement rows: the rest of its block, the start of the next block up to the window end, and the interpolated window end itself.
Rows that do not currently apply become free rows, so new periods or a new window only rewrite coefficients.

### Cost

$$
C = c_0 \, s_0 \, \Delta t_0 + \sum_{t=1}^{n} c_{t-1} \, s_t \, \Delta t_{t-1}
$$

where $c_k$ is the shortfall cost in \$/kWh/h for period $k$.
Each boundary is held for the period before it, and the first boundary, which has none, for the first period.

## Parameter mapping

| User configuration | Model field  | Notes                                                                     |
| ------------------ | ------------ | ------------------------------------------------------------------------- |
| Kind               | `kind`       | `reserve` or `headroom`                                                   |
| Loads              | `loads`      | Planned net power into each load                                          |
| Generation         | `generation` | Forecast power, the limits on the connections out of each generator       |
| Batteries          | `storage`    | Stored energy, limits, and the efficiency of their connections            |
| Window             | `window`     | Hours                                                                     |
| Level              | `level`      | Share of capacity at each boundary, or unset to use the min or max charge |
| Shortfall cost     | `price`      | \$/kWh/h                                                                  |

## Outputs

The required and available energy are reported in stored kWh, dividing the network-side values by $\bar{f}_t$.
The shortfall is $s_t$, which is already in stored kWh.

The buffer state of charge turns the requirement into a combined state of charge for the forecast card:

$$
\text{reserve:} \quad \frac{\sum_b B_{b,t} + R_t / \bar{f}_t}{\sum_b Q_{b,t}}
\qquad\qquad
\text{headroom:} \quad \frac{\sum_b B_{b,t} - R_t / \bar{f}_t}{\sum_b Q_{b,t}}
$$

clipped to 0-100%.
Its direction is the flow the line holds the batteries ready for: production (`+`) for a reserve, which keeps charge ready to discharge, and consumption (`-`) for headroom, which keeps room ready to charge.
The card uses it to tell which side of the line the batteries should stay on.

## Next steps

<div class="grid cards" markdown>

- :material-shield-check:{ .lg .middle } **Configure a buffer**

    ---

    Set up a reserve or headroom in Home Assistant.

    [:material-arrow-right: Buffer configuration](../../user-guide/elements/buffer.md)

- :material-battery:{ .lg .middle } **Battery modeling**

    ---

    See how batteries store the energy and space buffers count.

    [:material-arrow-right: Battery modeling](battery.md)

</div>
