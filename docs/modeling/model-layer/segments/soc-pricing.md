# SOC pricing segment

The `SocPricingSegment` adds cost terms when a connected battery's stored energy violates discharge
energy thresholds or charge capacity thresholds.
It uses slack variables to represent energy below or above thresholds and adds those slacks to the
objective.
This is intended for soft, price-based incentives rather than hard operating limits.

## Model formulation

### Parameters

| Parameter              | Description                                     | Units    |
| ---------------------- | ----------------------------------------------- | -------- |
| $E_{\text{dis}}(t)$    | Discharge energy threshold                      | kWh      |
| $E_{\text{chg}}(t)$    | Charge capacity threshold                       | kWh      |
| $c_{\text{dis}}(t)$    | Holding cost rate below the discharge threshold | \$/kWh/h |
| $c_{\text{chg}}(t)$    | Holding cost rate above the charge threshold    | \$/kWh/h |
| $E_{\text{stored}}(t)$ | Battery stored energy at the end of period $t$  | kWh      |
| $\Delta t(t)$          | Duration of period $t$                          | h        |

Thresholds are provided in the model coordinate system.
The prices are rates: they cost energy outside a threshold per hour it stays there, not per kWh moved.

## Rationale and usage

SOC pricing is useful when you want the optimizer to prefer certain operating ranges without
blocking feasible solutions.
Instead of adding hard constraints, the segment adds penalties (or incentives) that scale with the
amount of energy outside a threshold.
This keeps the model feasible while still signaling "avoid going below this reserve" or "avoid
filling beyond this headroom" as economic preferences.

Use cases include:

- Reserving a discharge buffer for uncertainty while still allowing emergency draw.
- Keeping headroom for anticipated solar while still allowing full charge if prices justify it.
- Shaping charge/discharge timing by combining base prices with SOC penalties.

The thresholds use the battery's model coordinate, so they align with the battery element's stored
energy state.
If your device or UI expresses thresholds in SOC percentage, convert to energy before passing to the
segment.

### Decision variables

| Variable            | Domain                | Description                            |
| ------------------- | --------------------- | -------------------------------------- |
| $S_{\text{dis}}(t)$ | $\mathbb{R}_{\geq 0}$ | Energy below discharge threshold       |
| $S_{\text{chg}}(t)$ | $\mathbb{R}_{\geq 0}$ | Energy above charge capacity threshold |

### Constraints

Discharge threshold slack:

$$
S_{\text{dis}}(t) \geq E_{\text{dis}}(t) - E_{\text{stored}}(t)
$$

Charge threshold slack:

$$
S_{\text{chg}}(t) \geq E_{\text{stored}}(t) - E_{\text{chg}}(t)
$$

### Cost contribution

$$
\text{Cost} = \sum_{t} \left[ S_{\text{dis}}(t) \cdot c_{\text{dis}}(t) + S_{\text{chg}}(t) \cdot c_{\text{chg}}(t) \right] \Delta t(t)
$$

Each term is kWh × \$/kWh/h × h, so the cost is in \$.
Multiplying by the period duration integrates the penalty over time.
A deficit therefore costs the same per hour whether the horizon uses short or long periods,
and the total grows with how long the battery stays outside the threshold.
For example, holding 1 kWh below the discharge threshold for 72 hours at 0.02 \$/kWh/h costs \$1.44.

## Physical interpretation

SOC pricing models a holding cost for keeping energy outside the discharge and charge thresholds.
These are soft constraints: the optimizer can violate thresholds when prices justify it.
Because the cost accrues per hour, short excursions that are quickly reversed are cheap,
while excursions that last for the rest of the horizon are expensive.

## Pricing partitions with opposing thresholds

You can model pricing for a specific energy band by pairing two SOC pricing segments with opposite
signs at different thresholds.
One segment can penalize energy below a lower threshold, while another provides a negative price
above an upper threshold.
The combination creates a net incentive to keep energy inside a band, while still allowing
economically justified deviations.

For example, to encourage the battery to stay between `E_low` and `E_high`:

- Set a positive `discharge_energy_price` below `E_low`.
- Set a negative `charge_capacity_price` above `E_high`.

This produces a "reward" for staying within the band and a "cost" for leaving it.
It is still a soft signal, so it will not block solutions if other costs dominate.

## Next steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connection model**

    ---

    Segment-based connection formulation.

    [:material-arrow-right: Connection formulation](../connections/connection.md)

- :material-layers:{ .lg .middle } **Segments**

    ---

    Browse all connection segment types.

    [:material-arrow-right: Segment index](index.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code for the SOC pricing segment.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/core/model/elements/segments/soc_pricing.py)

</div>
