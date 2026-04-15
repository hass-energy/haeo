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

The `NetworkElement` base class creates per-tag power balance constraints at each element.
Production and consumption are each decomposed into per-tag variables with sum constraints:

$$
\sum_{k \in \text{outbound}} P_k(t) = P_{\text{produced}}(t), \quad
\sum_{k \in \text{inbound}} C_k(t) = P_{\text{consumed}}(t)
$$

For each tag $k$ present on connected connections:

**If $k$ is in `outbound_tags` or `inbound_tags`**:

$$
P_{\text{conn},k}(t) + P_k(t) - C_k(t) = 0
$$

Where $P_k(t)$ is the per-tag production variable (zero if $k \notin$ `outbound_tags`)
and $C_k(t)$ is the per-tag consumption variable (zero if $k \notin$ `inbound_tags`).

**If $k$ is in neither set (blocked)**:

Each connection's per-tag flow at this element is individually forced to zero:

$$
P_{\text{conn},k,i}(t) = 0 \quad \forall i \in \text{connections}
$$

This prevents pass-through of blocked tags even across multiple connections.

If an element has production but no outbound tags overlap with connection tags,
production is forced to zero. Likewise for consumption with no inbound overlap.

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

## Next steps

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
