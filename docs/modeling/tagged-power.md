# Tagged power

Tagged power enables per-source tracking of power flows through the network.
Each unit of power carries a tag identifying its origin, allowing the optimizer to apply different costs or constraints based on where power was produced.

## Concept

In a standard optimization, power is fungible — the solver only sees total flows on each connection.
Tagged power assigns integer tags to power sources, then decomposes each flow into per-tag components.
This is analogous to VLANs in networking: power on different tags shares the same physical connections but is tracked separately.

**Use cases**:

- **Per-source export pricing**: Charge different feed-in rates for solar vs battery exports
- **Source-restricted consumption**: Ensure a load only draws from specific sources
- **Policy enforcement**: Implement power routing policies (e.g., "solar power cannot charge the battery")

## Formulation

### Element power protocol

Every element declares its power production and consumption separately:

- `element_power_produced()`: Power injected into the network (positive, ≥ 0)
- `element_power_consumed()`: Power absorbed from the network (positive, ≥ 0)

Production is placed on the element's `outbound_tags`.
Consumption draws from the element's `inbound_tags`.

### Tag parameters

| Parameter       | Scope           | Description                                            |
| --------------- | --------------- | ------------------------------------------------------ |
| `outbound_tags` | Element         | Tags that produced power can be placed on (None = all) |
| `inbound_tags`  | Element         | Tags that consumed power can draw from (None = all)    |
| `tags`          | Connection      | Set of tags carried on this connection                 |
| `tag_prices`    | Pricing segment | Per-tag price adjustments (`{tag, price}` entries)     |

### Connection tag decomposition

When a connection has tags, its total flow is decomposed into per-tag flow variables:

$$
P_{\text{in}}(t) = \sum_{k \in \text{tags}} P_{\text{in},k}(t), \quad P_{\text{in},k}(t) \geq 0
$$

Segment transforms (efficiency) are applied proportionally to each tag.
See [Connection tag decomposition](model-layer/connections/connection.md#tag-decomposition) for details.

### Per-tag balance

The Element base class creates per-tag power balance constraints at each element.
For each tag $k$ present on connected connections:

**If $k$ is in `outbound_tags`**:

$$
P_{\text{conn},k}(t) + P_{\text{produced}}(t) - C_k(t) = 0
$$

Production appears on outbound tags, plus any consumption routed from this tag.

**If $k$ is in `inbound_tags`** (but not in `outbound_tags`):

$$
P_{\text{conn},k}(t) - C_k(t) = 0
$$

Only consumption can be routed from inbound tags.

**If $k$ is in neither set**:

$$
P_{\text{conn},k}(t) = 0
$$

No power on this tag can enter or leave the element.

Where $C_k(t) \geq 0$ are per-tag consumption variables.
A sum constraint ensures all consumption is accounted for:

$$
\sum_{k \in \text{allowed}} C_k(t) = P_{\text{consumed}}(t)
$$

### Tag costs on connections

Each `tag_prices` entry adds a per-tag surcharge to the connection.
For tag $k$ with price $c_k$:

$$
\text{Cost}_k = \sum_t c_k \cdot P_{\text{in},k}(t) \cdot \Delta t
$$

This is additive with the connection's base pricing segment.

## Example

Consider a system with solar, battery, grid, and load connected through a switchboard:

| Element | `outbound_tags` | `inbound_tags` | Role                         |
| ------- | --------------- | -------------- | ---------------------------- |
| Solar   | \{1}            | —              | Source only, produces tag 1  |
| Battery | \{2}            | {1, 2, 3}      | Produces tag 2, consumes all |
| Grid    | \{3}            | {1, 2, 3}      | Produces tag 3, consumes all |
| Load    | —               | {1, 2, 3}      | Sink only, consumes all      |

With `tag_prices` on the grid export connection:

- Solar export (tag 1): +\$0.02/kWh surcharge
- Battery export (tag 2): +\$0.10/kWh surcharge

The optimizer can now distinguish the cost of exporting solar-sourced vs battery-sourced power, routing exports to minimize total cost.

## Next Steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connection tags**

    ---

    Per-tag flow decomposition on connections.

    [:material-arrow-right: Connection model](model-layer/connections/connection.md#tag-decomposition)

- :material-battery-charging:{ .lg .middle } **Battery model**

    ---

    Produced/consumed power for energy storage.

    [:material-arrow-right: Battery formulation](model-layer/elements/battery.md)

- :material-transit-connection-variant:{ .lg .middle } **Node model**

    ---

    Source/sink power with tag routing.

    [:material-arrow-right: Node formulation](model-layer/elements/node.md)

</div>
