# Pricing segment

The `PricingSegment` adds directional transfer costs to the objective function.
It models wheeling charges, conversion fees, or any cost associated with power flow.

## Model formulation

### Parameters

| Parameter             | Description                              | Default |
| --------------------- | ---------------------------------------- | ------- |
| $c_{s \rightarrow t}$ | Price for source to target flow (\$/kWh) | None    |
| $c_{t \rightarrow s}$ | Price for target to source flow (\$/kWh) | None    |

Parameters can be scalars or per-period arrays.
Scalar values are broadcast across all periods.

### Decision variables

| Variable              | Domain                | Description                      |
| --------------------- | --------------------- | -------------------------------- |
| $P_{s \rightarrow t}$ | $\mathbb{R}_{\geq 0}$ | Power flow from source to target |
| $P_{t \rightarrow s}$ | $\mathbb{R}_{\geq 0}$ | Power flow from target to source |

### Cost contribution

If pricing is configured, the segment contributes to the objective function:

$$
\text{Cost} = \sum_{t} \left[ c_{s \rightarrow t}(t) \cdot P_{s \rightarrow t}(t) + c_{t \rightarrow s}(t) \cdot P_{t \rightarrow s}(t) \right] \cdot \Delta t
$$

where $\Delta t$ is the time period in hours.

The segment does not add constraints.

## Physical interpretation

Pricing models transfer fees, wheeling charges, or conversion costs.
Costs can vary over time and by direction.

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

    View the source code for the pricing segment.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/elements/segments/pricing.py)

</div>
