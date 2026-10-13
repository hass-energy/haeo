# Holding cost

A holding cost charges a rate for energy a battery stores above or below a threshold,
for every hour it stays there.
It is a soft preference rather than a hard limit:
the optimizer goes past the threshold whenever that earns more than holding the energy there costs.

A holding cost adds cost without taking part in the power balance.
It references a [battery](battery.md) by name and reads that battery's stored energy,
so any number of holding costs can apply to one battery and their costs add up.

## Model formulation

### Parameters

| Parameter              | Description                                    | Units    |
| ---------------------- | ---------------------------------------------- | -------- |
| $d$                    | Direction: above or below the threshold        | -        |
| $E_{\text{th}}(t)$     | Threshold at the end of period $t$             | kWh      |
| $c(t)$                 | Holding cost rate                              | \$/kWh/h |
| $E_{\text{stored}}(t)$ | Battery stored energy at the end of period $t$ | kWh      |
| $\Delta t(t)$          | Duration of period $t$                         | h        |

The threshold is in the battery's own energy coordinate, the same one as its stored energy.

### Decision variables

| Variable | Domain                | Description                                 |
| -------- | --------------------- | ------------------------------------------- |
| $S(t)$   | $\mathbb{R}_{\geq 0}$ | Energy past the threshold at the end of $t$ |

### Constraints

For a holding cost below the threshold:

$$
S(t) \geq E_{\text{th}}(t) - E_{\text{stored}}(t)
$$

For a holding cost above the threshold:

$$
S(t) \geq E_{\text{stored}}(t) - E_{\text{th}}(t)
$$

Minimizing cost pushes $S(t)$ down onto the larger of zero and the distance past the threshold.

### Cost contribution

$$
\text{Cost} = \sum_{t} S(t) \cdot c(t) \cdot \Delta t(t)
$$

Each term is kWh × \$/kWh/h × h, so the cost is in \$.
Multiplying by the period duration integrates the cost over time,
so a kWh past the threshold costs the same per hour whether the horizon uses short or long periods.
For example, holding 1 kWh below the threshold for 72 hours at 0.02 \$/kWh/h costs \$1.44.

## Physical interpretation

A holding cost below a threshold keeps a reserve:
energy below it is used for short price spikes and refilled soon afterwards,
because a deficit that lasts for the rest of the horizon costs much more than one that lasts an hour.
A holding cost above a threshold keeps headroom the same way,
filling the top of the battery only shortly before that energy is used.

The rate must not be negative.
A negative rate would reward an unbounded amount of energy past the threshold, which makes the problem unbounded.

## Next steps

<div class="grid cards" markdown>

- :material-battery-charging:{ .lg .middle } **Battery model**

    ---

    Energy storage whose stored energy a holding cost applies to.

    [:material-arrow-right: Battery formulation](battery.md)

- :material-battery-heart-variant:{ .lg .middle } **Battery device**

    ---

    How battery holding costs map onto this element.

    [:material-arrow-right: Battery device layer](../../device-layer/battery.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code for the holding cost element.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/core/model/elements/holding_cost.py)

</div>
