# SOC pricing segment

The `SocPricingSegment` adds cost terms when a connected battery's stored energy is above or below
a configured energy threshold.
It uses slack variables to represent energy above and below the threshold and adds those slacks to
the objective.
This is intended for soft, price-based incentives rather than hard operating limits.

## Model formulation

### Parameters

| Parameter              | Description                              | Units  |
| ---------------------- | ---------------------------------------- | ------ |
| $E_{\text{thr}}(t)$    | Energy threshold                         | kWh    |
| $c_{\text{dis}}(t)$    | Penalty price below threshold            | \$/kWh |
| $c_{\text{chg}}(t)$    | Penalty price above threshold            | \$/kWh |
| $E_{\text{stored}}(t)$ | Battery stored energy (model coordinate) | kWh    |

Thresholds are provided in the model coordinate system.

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

| Variable             | Domain                | Description                  |
| -------------------- | --------------------- | ---------------------------- |
| $S_{\text{dis}}(t)$  | $\mathbb{R}_{\geq 0}$ | Energy below the threshold   |
| $S_{\text{chg}}(t)$  | $\mathbb{R}_{\geq 0}$ | Energy above the threshold   |

### Constraints

Below-threshold slack:

$$
S_{\text{dis}}(t) \geq E_{\text{thr}}(t) - E_{\text{stored}}(t)
$$

Above-threshold slack:

$$
S_{\text{chg}}(t) \geq E_{\text{stored}}(t) - E_{\text{thr}}(t)
$$

### Cost contribution

$$
\text{Cost} = \sum_{t} \left[ S_{\text{dis}}(t) \cdot c_{\text{dis}}(t) + S_{\text{chg}}(t) \cdot c_{\text{chg}}(t) \right]
$$

## Physical interpretation

SOC pricing models economic penalties for operating outside discharge and charge thresholds.
These are soft constraints: the optimizer can violate thresholds when prices justify it.

## Pricing partitions with opposing thresholds

You can model pricing for a specific energy band by pairing two SOC pricing segments with
different thresholds and using one-sided prices:

- A segment at the lower threshold with `discharge_price > 0` and `charge_price = 0` penalizes being below the band.
- A segment at the upper threshold with `charge_price > 0` and `discharge_price = 0` penalizes being above the band.

For example, to encourage the battery to stay between `E_low` and `E_high`:

- Configure a segment with threshold `E_low` and a positive below-threshold penalty (`discharge_price`).
- Configure a segment with threshold `E_high` and a positive above-threshold penalty (`charge_price`).

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

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/elements/segments/soc_pricing.py)

</div>
