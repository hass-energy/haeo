# SOC pricing segment

The `SocPricingSegment` adds cost terms when a connected battery's stored energy violates discharge
energy thresholds or charge capacity thresholds.
It uses slack variables to represent energy below or above thresholds and adds those slacks to the
objective.

## Model formulation

### Parameters

| Parameter              | Description                              | Units  |
| ---------------------- | ---------------------------------------- | ------ |
| $E_{\text{dis}}(t)$    | Discharge energy threshold               | kWh    |
| $E_{\text{chg}}(t)$    | Charge capacity threshold                | kWh    |
| $c_{\text{dis}}(t)$    | Discharge threshold penalty price        | \$/kWh |
| $c_{\text{chg}}(t)$    | Charge threshold penalty price           | \$/kWh |
| $E_{\text{stored}}(t)$ | Battery stored energy (model coordinate) | kWh    |

Thresholds are provided in the model coordinate system.

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
\text{Cost} = \sum_{t} \left[ S_{\text{dis}}(t) \cdot c_{\text{dis}}(t) + S_{\text{chg}}(t) \cdot c_{\text{chg}}(t) \right]
$$

## Physical interpretation

SOC pricing models economic penalties for operating outside discharge and charge thresholds.
These are soft constraints: the optimizer can violate thresholds when prices justify it.

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
