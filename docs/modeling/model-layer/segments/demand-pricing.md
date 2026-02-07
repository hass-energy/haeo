# Demand pricing segment

The `DemandPricingSegment` adds peak demand charges based on block-average power.
It models tariffs that charge for the highest average kW within a demand price schedule.

## Model formulation

### Parameters

| Parameter                | Description                                        | Default |
| ------------------------ | -------------------------------------------------- | ------- |
| $c_{s \rightarrow t}(t)$ | Demand price schedule for source to target (\$/kW) | None    |
| $c_{t \rightarrow s}(t)$ | Demand price schedule for target to source (\$/kW) | None    |
| $E_{s \rightarrow t}$    | Demand energy already used in current block (kWh)  | 0       |
| $E_{t \rightarrow s}$    | Demand energy already used in current block (kWh)  | 0       |
| $E^{\max}_{s \rightarrow t}$ | Peak demand energy in current billing cycle (kWh) | 0       |
| $E^{\max}_{t \rightarrow s}$ | Peak demand energy in current billing cycle (kWh) | 0       |
| $B$                      | Demand block duration (hours)                      | 0.5     |

Demand prices can be time-varying.
Block duration is a scalar.

### Decision variables

| Variable                          | Domain                | Description                                              |
| --------------------------------- | --------------------- | -------------------------------------------------------- |
| $C_{\text{peak},s \rightarrow t}$ | $\mathbb{R}_{\geq 0}$ | Peak block-average demand cost for source to target flow |
| $C_{\text{peak},t \rightarrow s}$ | $\mathbb{R}_{\geq 0}$ | Peak block-average demand cost for target to source flow |

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
C_{\text{peak}} \ge \bar{c}_b \cdot \bar{P}_b
$$

If $E^{\max}$ is provided, the peak cost also respects the existing billing cycle peak:

$$
C_{\text{peak}} \ge \bar{c}_b \cdot \frac{E^{\max}}{B}
$$

Block prices $\bar{c}_b$ are derived from the demand price schedule using the same block weights.
Blocks with zero demand price do not affect the peak cost.

### Cost contribution

If demand pricing is configured, the segment contributes:

$$
	ext{Cost} = C_{\text{peak}}
$$

The formulation is linear and uses a single peak variable per direction.

## Physical interpretation

Demand pricing models peak demand charges commonly used by utilities.
The optimizer avoids high block-average imports during periods with nonzero demand prices.

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
