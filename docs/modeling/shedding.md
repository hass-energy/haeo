# Load shedding via threshold price

Sheddable loads (curtailment enabled) can be configured with a **threshold price** in \$/kWh.
The optimizer serves the load only while the marginal value of energy at its connection node is at or below the threshold; above that, the load sheds.

## What "connection node" means

The threshold is **not** compared against the grid import tariff directly.
It is compared against the **shadow price (LP dual) of the node the load is connected to** — that is, the node selected in the load's *Connection* field.

The shadow price at a node is the cheapest \$/kWh way the optimizer can supply one more kWh of demand at that point in the network, given **all** active constraints in that interval.
When the load is connected to a Switchboard node, the relevant price is therefore the minimum of (subject to feasibility):

- the grid import tariff,
- the marginal cost of discharging a battery (its own dual),
- the marginal cost of curtailing solar export (its own dual),
- the marginal cost of curtailing another sheddable load on the same node, and so on.

If solar or battery is available cheaper than the grid tariff, the switchboard's \$/kWh dual will track that cheaper source, not the tariff.
This means a load can keep running even while grid prices are high, as long as something cheaper is delivering energy to its node.

In short: the threshold acts on the **node** the load sees, after the LP has already worked out the cheapest local supply mix.
If you want the threshold to act directly on the grid tariff, connect the load to the grid element rather than to an intermediate switchboard.

The matching shadow-price sensor for the connection node is exposed by every node device — for example, a switchboard called *Switchboard* exposes `sensor.switchboard_node_power_balance_energy_price` in \$/kWh.
Dashboard this sensor alongside the load's `threshold_price` sensor to see the comparison directly.

## How the threshold encodes a willingness to pay

The threshold-price field is implemented as an extra `PricingSegment` on the load's connection.
The segment contributes `qsum(p_load × price × Δt)` to the LP objective.
Because the optimizer **minimises** the objective, the segment uses `price = -threshold_price` so that serving the load is a *benefit* (a negative cost) of `threshold_price × p_load × Δt` per period.

Equivalently: each kWh delivered to the load earns the system a credit of one `threshold_price`, paid out of the same objective that imports and exports settle through.
The optimizer will serve the load whenever doing so reduces the objective — i.e. whenever the marginal cost of supplying that kWh (the connection node's \$/kWh dual) is below `threshold_price`.

## Worked example

Consider a sheddable load with `forecast = 5 kW` always, `curtailment = true`, and `threshold_price = $0.30/kWh`, connected to a switchboard that imports from the grid at a price stepping across four 1-hour periods:

| Period | Grid \$/kWh | Switchboard \$/kWh dual | Served? | `load_power` |
| ------ | ----------- | ----------------------- | ------- | ------------ |
| 1      | 0.20        | 0.20                    | Yes     | 5 kW         |
| 2      | 0.25        | 0.25                    | Yes     | 5 kW         |
| 3      | 0.35        | 0.35                    | No      | 0 kW         |
| 4      | 0.40        | 0.40                    | No      | 0 kW         |

The shedding decision is exactly the comparison between the load's **threshold price** sensor and the switchboard's **node power balance \$/kWh** shadow-price sibling (see [Shadow prices — per-power vs per-energy](shadow-prices.md#per-power-vs-per-energy)).
Both sensors are emitted in the same units (\$/kWh) so a Lovelace dashboard can plot them on the same axis.

In this example the switchboard's dual exactly tracks the grid tariff because no cheaper source is available.
In a real install with battery and solar, the dual would often dip below the grid tariff during the day, so a load with `threshold_price = $0.30/kWh` could keep running through a \$0.40/kWh grid hour if the battery was discharging at a marginal cost below \$0.30/kWh.

## When the threshold is ignored

The threshold price has no effect when `curtailment = false`: a fixed load is constrained to equal its forecast at every period, so the optimizer cannot trade dispatch against price.
The adapter omits the pricing segment in that case rather than letting it silently waste solver effort.

A threshold price of \$0 (the default after migration) is equivalent to no threshold: the objective term is exactly zero and the LP solution is unchanged from pre-threshold behaviour.

## Setting the threshold

The threshold can be configured as a constant (e.g. \$0.30/kWh) or bound to an entity that supplies a time-varying price (e.g. a tariff sensor or a forecast).
It is **not** the same as the energy tariff itself — it is the user's willingness to pay for *this load* at *this time*.
A higher threshold makes the load more important and less likely to shed; a lower threshold makes it more discretionary.

## Forecast statistics sensors

Every Load element also exposes cumulative and rolling-24h statistics derived from the LP solution, so a dashboard can show "what this load will consume and cost over the optimization horizon" without any template plumbing:

| Sensor               | Window       | What it answers                                                                        |
| -------------------- | ------------ | -------------------------------------------------------------------------------------- |
| `total_energy`       | full horizon | Forecast energy (kWh) the load will be served                                          |
| `total_cost`         | full horizon | Marginal cost (\$) the load contributes against the source-node dual                   |
| `total_runtime`      | full horizon | Hours the load is dispatched (power > 0) within the horizon                            |
| `total_average_cost` | full horizon | Energy-weighted average \$/kWh paid for the load (`total_cost / total_energy`)         |
| `daily_energy`       | next 24h     | Same as above but restricted to the first 24h of the horizon (rolling window from now) |
| `daily_cost`         | next 24h     | "                                                                                      |
| `daily_runtime`      | next 24h     | "                                                                                      |
| `daily_average_cost` | next 24h     | "                                                                                      |

The cost integral is `Σ p_load[t] × node_dual[t]`, where `node_dual[t]` is the **source-node power-balance shadow price** already period-integrated by the LP objective.
This stays correct whether the load is dispatched, shed, or partially served: in shed periods `p_load[t] = 0`, contributing zero, and in served periods the dual reflects the true marginal cost (which can be the grid tariff, a battery's discharge cost, or solar curtailment value, depending on which source is on the margin).

`average_cost` falls back to \$0/kWh whenever `total_energy` is zero, so a fully-shed load reports zeros across the board rather than a divide-by-zero error.
