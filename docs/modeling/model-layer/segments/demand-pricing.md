# Demand pricing segment

The `DemandPricingSegment` adds peak demand charges based on block-average power.
It models tariffs that charge for the highest average kW within demand windows.

## Model formulation

### Parameters

| Parameter                | Description                                        | Default |
| ------------------------ | -------------------------------------------------- | ------- |
| $w_{s \rightarrow t}(t)$ | Demand window weight for source to target periods  | None    |
| $w_{t \rightarrow s}(t)$ | Demand window weight for target to source periods  | None    |
| $c_{s \rightarrow t}$    | Demand price for source to target peak (\$/kW/day) | None    |
| $c_{t \rightarrow s}$    | Demand price for target to source peak (\$/kW/day) | None    |
| $E_{s \rightarrow t}$    | Demand energy already used in current block (kWh)  | 0       |
| $E_{t \rightarrow s}$    | Demand energy already used in current block (kWh)  | 0       |
| $B$                      | Demand block duration (hours)                      | 0.5     |
| $D$                      | Billing days multiplier                            | 1       |

Window weights are normalized to $[0, 1]$ and can be time-varying.
Block duration and billing days are scalars.

### Decision variables

| Variable                          | Domain                | Description                                        |
| --------------------------------- | --------------------- | -------------------------------------------------- |
| $P_{\text{peak},s \rightarrow t}$ | $\mathbb{R}_{\geq 0}$ | Peak block-average power for source to target flow |
| $P_{\text{peak},t \rightarrow s}$ | $\mathbb{R}_{\geq 0}$ | Peak block-average power for target to source flow |

### Block averages

The horizon is divided into blocks of length $B$ hours.
Each block average is computed from interval power values using overlap weights.
For a block $b$, the average power is:

$$
\bar{P}_b = \sum_{t} \alpha_{b,t} \cdot P(t)
$$

where $\alpha_{b,t}$ is the fraction of period $t$ that overlaps block $b$.
The weights sum to 1 within each block.
If $E$ is provided, it is added to the first block energy before averaging.

### Constraints

For each block $b$:

$$
P_{\text{peak}} \ge w_b \cdot \bar{P}_b
$$

Window weights $w_b$ are derived from the demand window time series.
Blocks outside demand windows use $w_b = 0$ and do not affect the peak.

### Cost contribution

If demand pricing is configured, the segment contributes:

$$
\text{Cost} = P_{\text{peak}} \cdot c_{\text{demand}} \cdot D
$$

The formulation is linear and uses a single peak variable per direction.

## Physical interpretation

Demand pricing models peak demand charges commonly used by utilities.
The optimizer avoids high block-average imports during demand windows when the price is significant.

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

    View the source code for the demand pricing segment.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/elements/segments/demand_pricing.py)

</div>
