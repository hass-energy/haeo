# Passthrough segment

The `PassthroughSegment` provides lossless flow with no constraints or costs.
It is used as the default segment when a connection has no explicit segments configured.

## Model formulation

### Decision variables

| Variable              | Domain                | Description                      |
| --------------------- | --------------------- | -------------------------------- |
| $P_{s \rightarrow t}$ | $\mathbb{R}_{\geq 0}$ | Power flow from source to target |
| $P_{t \rightarrow s}$ | $\mathbb{R}_{\geq 0}$ | Power flow from target to source |

### Constraints

The passthrough segment does not add constraints.
Power entering the segment equals power leaving the segment in both directions.

## Physical interpretation

This segment models an ideal, lossless connection with no capacity limits or pricing.
It is useful for implicit connections created by device adapters.

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

    View the source code for the passthrough segment.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/elements/segments/passthrough.py)

</div>
