# Tag Pricing Segment

The tag pricing segment adds transfer costs for a specific tagged category of power flow.

## Formulation

The tag pricing segment is lossless (in == out) and adds cost to the objective:

$$
\text{cost}_{st} = \sum_{t} P^{st}_t \cdot \pi^{st}_t \cdot \Delta t_t
$$

$$
\text{cost}_{ts} = \sum_{t} P^{ts}_t \cdot \pi^{ts}_t \cdot \Delta t_t
$$

Where:

- $P^{st}_t$, $P^{ts}_t$ are the power flow variables for each direction
- $\pi^{st}_t$, $\pi^{ts}_t$ are the prices in $/kWh
- $\Delta t_t$ is the period duration in hours

## Tag Field

The `tag` field is a string identifying which category of power flow this segment prices.
Multiple tag pricing segments with different tags can coexist on the same connection, each pricing a different category independently.

## Parameters

| Parameter | Type | Unit | Description |
|-----------|------|------|-------------|
| `tag` | str | — | Power flow category identifier |
| `price_source_target` | float or array | $/kWh | Price for source→target flow |
| `price_target_source` | float or array | $/kWh | Price for target→source flow |

## Source

:material-github: [`segments/tag_pricing.py`](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/core/model/elements/segments/tag_pricing.py)
