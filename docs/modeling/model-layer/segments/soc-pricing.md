# SOC pricing segment

The `SocPricingSegment` adds cost terms when a connected battery's stored energy sits outside configured energy thresholds.
It uses slack variables to represent energy below or above thresholds and adds those slacks to the objective.

## Model formulation

### Parameters

| Parameter              | Description                              | Units  |
| ---------------------- | ---------------------------------------- | ------ |
| $E_{\text{low}}(t)$    | Lower energy threshold                   | kWh    |
| $E_{\text{high}}(t)$   | Upper energy threshold                   | kWh    |
| $c_{\text{low}}(t)$    | Lower threshold penalty price            | \$/kWh |
| $c_{\text{high}}(t)$   | Upper threshold penalty price            | \$/kWh |
| $E_{\text{stored}}(t)$ | Battery stored energy (model coordinate) | kWh    |

Thresholds are provided in the model coordinate system.

### Decision variables

| Variable             | Domain                | Description                  |
| -------------------- | --------------------- | ---------------------------- |
| $S_{\text{low}}(t)$  | $\mathbb{R}_{\geq 0}$ | Energy below lower threshold |
| $S_{\text{high}}(t)$ | $\mathbb{R}_{\geq 0}$ | Energy above upper threshold |

### Constraints

Lower threshold slack:

$$
S_{\text{low}}(t) \geq E_{\text{low}}(t) - E_{\text{stored}}(t)
$$

Upper threshold slack:

$$
S_{\text{high}}(t) \geq E_{\text{stored}}(t) - E_{\text{high}}(t)
$$

### Cost contribution

$$
\text{Cost} = \sum_{t} \left[ S_{\text{low}}(t) \cdot c_{\text{low}}(t) + S_{\text{high}}(t) \cdot c_{\text{high}}(t) \right]
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
