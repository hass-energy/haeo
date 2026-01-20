# Power limit segment

The `PowerLimitSegment` enforces directional capacity limits on connection flow.
It can also apply a time-slice constraint that prevents simultaneous full-capacity flow in both directions.

## Model formulation

### Parameters

| Parameter                    | Description                              | Default   |
| ---------------------------- | ---------------------------------------- | --------- |
| $P^{\max}_{s \rightarrow t}$ | Maximum power from source to target (kW) | Unlimited |
| $P^{\max}_{t \rightarrow s}$ | Maximum power from target to source (kW) | Unlimited |
| `fixed`                      | Enforce equality instead of inequality   | False     |

Parameters can be scalars or per-period arrays.
Scalar values are broadcast across all periods.

### Decision variables

| Variable              | Domain                | Description                      |
| --------------------- | --------------------- | -------------------------------- |
| $P_{s \rightarrow t}$ | $\mathbb{R}_{\geq 0}$ | Power flow from source to target |
| $P_{t \rightarrow s}$ | $\mathbb{R}_{\geq 0}$ | Power flow from target to source |

### Constraints

#### Directional limits

When power limits are configured:

$$
0 \leq P_{s \rightarrow t}(t) \leq P_{s \rightarrow t}^{\max}(t) \quad \forall t
$$

$$
0 \leq P_{t \rightarrow s}(t) \leq P_{t \rightarrow s}^{\max}(t) \quad \forall t
$$

If `fixed=True`, these become equality constraints.

**Shadow prices**:
The `segments.power_limit.source_target` and `segments.power_limit.target_source` outputs provide the marginal value of relaxing these constraints.

#### Time-slice coupling

When both power limits are set, the segment adds a time-slice constraint:

$$
\frac{P_{s \rightarrow t}(t)}{P_{s \rightarrow t}^{\max}(t)} + \frac{P_{t \rightarrow s}(t)}{P_{t \rightarrow s}^{\max}(t)} \leq 1 \quad \forall t
$$

This models physical limitations of bidirectional devices (for example, inverters that cannot simultaneously charge and discharge at full rate).

**Shadow price**:
The `segments.power_limit.time_slice` output reports the marginal value of the coupling constraint.

## Physical interpretation

Directional limits model hard capacity constraints such as cable ratings or inverter limits.
Time-slice coupling models shared hardware constraints that prohibit full flow in both directions at once.

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

    View the source code for the power limit segment.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/elements/segments/power_limit.py)

</div>
