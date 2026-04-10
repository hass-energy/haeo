# Tag Filter Segment

The tag filter segment constrains power flow for a specific tagged category.

## Formulation

The tag filter segment is lossless (in == out) and adds directional constraints:

$$
P^{st}_t \leq P^{st}_{max,t}
$$

$$
P^{ts}_t \leq P^{ts}_{max,t}
$$

Where:

- $P^{st}_t$, $P^{ts}_t$ are the power flow variables for each direction
- $P^{st}_{max,t}$, $P^{ts}_{max,t}$ are the maximum allowed power

Set `max_power` to 0 to completely block a tagged power flow in that direction.

## Tag Field

The `tag` field is a string identifying which category of power flow this segment constrains.
This allows selective filtering of specific power sources while allowing others to flow freely.

## Parameters

| Parameter | Type | Unit | Description |
|-----------|------|------|-------------|
| `tag` | str | — | Power flow category identifier |
| `max_power_source_target` | float or array | kW | Max power for source→target flow |
| `max_power_target_source` | float or array | kW | Max power for target→source flow |

## Shadow Prices

Both constraints expose shadow prices (output=True), indicating the marginal cost of the power limit in $/kW.

## Source

:material-github: [`segments/tag_filter.py`](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/core/model/elements/segments/tag_filter.py)
