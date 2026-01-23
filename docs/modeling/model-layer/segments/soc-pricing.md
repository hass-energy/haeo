# SOC pricing segment

The `SocPricingSegment` adds cost terms when a connected battery's stored energy sits outside configured SOC thresholds.
It uses slack variables to represent the energy below or above thresholds and adds those slacks to the objective.

## Model formulation

### Parameters

| Parameter              | Description                              | Units  |
| ---------------------- | ---------------------------------------- | ------ |
| $E_{\text{min}}(t)$    | Undercharge energy threshold             | kWh    |
| $E_{\text{max}}(t)$    | Overcharge energy threshold              | kWh    |
| $c_{\text{under}}(t)$  | Undercharge penalty price                | \$/kWh |
| $c_{\text{over}}(t)$   | Overcharge penalty price                 | \$/kWh |
| $E_{\text{stored}}(t)$ | Battery stored energy (model coordinate) | kWh    |

Thresholds are provided in the model coordinate system.
When an undercharge range is configured, $E_{\text{stored}}$ is measured relative to the lower SOC bound.

### Decision variables

| Variable              | Domain                | Description                        |
| --------------------- | --------------------- | ---------------------------------- |
| $S_{\text{under}}(t)$ | $\mathbb{R}_{\geq 0}$ | Energy below undercharge threshold |
| $S_{\text{over}}(t)$  | $\mathbb{R}_{\geq 0}$ | Energy above overcharge threshold  |

### Constraints

Undercharge slack:

$$
S_{\text{under}}(t) \geq E_{\text{min}}(t) - E_{\text{stored}}(t)
$$

Overcharge slack:

$$
S_{\text{over}}(t) \geq E_{\text{stored}}(t) - E_{\text{max}}(t)
$$

### Cost contribution

$$
\text{Cost} = \sum_{t} \left[ S_{\text{under}}(t) \cdot c_{\text{under}}(t) + S_{\text{over}}(t) \cdot c_{\text{over}}(t) \right]
$$

## Physical interpretation

SOC pricing models economic penalties for operating outside the preferred SOC range.
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
