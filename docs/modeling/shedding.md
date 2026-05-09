# Load shedding via threshold price

Sheddable loads (curtailment enabled) can be configured with a **threshold price** in \$/kWh.
The optimizer serves the load only while the marginal value of energy at its connection node is at or below the threshold; above that, the load sheds.

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

The shedding decision is exactly the comparison between the load's **threshold price** sensor and the switchboard's **\$/kWh** shadow-price sibling (see [Shadow prices — per-power vs per-energy](shadow-prices.md#per-power-vs-per-energy)).
Both sensors are emitted in the same units (\$/kWh) so a Lovelace dashboard can plot them on the same axis.

## When the threshold is ignored

The threshold price has no effect when `curtailment = false`: a fixed load is constrained to equal its forecast at every period, so the optimizer cannot trade dispatch against price.
The adapter omits the pricing segment in that case rather than letting it silently waste solver effort.

A threshold price of \$0 (the default after migration) is equivalent to no threshold: the objective term is exactly zero and the LP solution is unchanged from pre-threshold behaviour.

## Setting the threshold

The threshold can be configured as a constant (e.g. \$0.30/kWh) or bound to an entity that supplies a time-varying price (e.g. a tariff sensor or a forecast).
It is **not** the same as the energy tariff itself — it is the user's willingness to pay for *this load* at *this time*.
A higher threshold makes the load more important and less likely to shed; a lower threshold makes it more discretionary.
