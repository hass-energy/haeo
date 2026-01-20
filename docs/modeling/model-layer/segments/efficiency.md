# Efficiency segment

The `EfficiencySegment` applies direction-specific efficiency ratios to power flow.
It models losses that occur during transfer, such as inverter or transformer losses.

## Model formulation

### Parameters

| Parameter                | Description                       | Default |
| ------------------------ | --------------------------------- | ------- |
| $\eta_{s \rightarrow t}$ | Source to target efficiency ratio | 1.0     |
| $\eta_{t \rightarrow s}$ | Target to source efficiency ratio | 1.0     |

Efficiency values are ratios in the range $(0, 1]$.
Input entities normalize percentage values to ratios before reaching the model.

### Decision variables

The segment uses the connection flow variables as its inputs:

| Variable                          | Domain                | Description                                     |
| --------------------------------- | --------------------- | ----------------------------------------------- |
| $P^{\text{in}}_{s \rightarrow t}$ | $\mathbb{R}_{\geq 0}$ | Power entering the segment in the s→t direction |
| $P^{\text{in}}_{t \rightarrow s}$ | $\mathbb{R}_{\geq 0}$ | Power entering the segment in the t→s direction |

### Transformation

The efficiency segment scales power leaving the segment:

$$
P^{\text{out}}_{s \rightarrow t}(t) = P^{\text{in}}_{s \rightarrow t}(t) \cdot \eta_{s \rightarrow t}(t)
$$

$$
P^{\text{out}}_{t \rightarrow s}(t) = P^{\text{in}}_{t \rightarrow s}(t) \cdot \eta_{t \rightarrow s}(t)
$$

The segment does not introduce additional constraints.

## Physical interpretation

Losses are applied to power arriving at the destination.
Power leaving a source is not scaled, but power entering the next segment is reduced by the efficiency ratio.

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

    View the source code for the efficiency segment.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/elements/segments/efficiency.py)

</div>
