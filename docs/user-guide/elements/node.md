# Node

A node is a point in your network that can produce and/or consume unlimited power at no cost.
Use it to build a custom endpoint when no other element fits, and put the limits and prices on the connections to it.

!!! warning "Advanced Element"

    Creating nodes requires **Advanced Mode** to be enabled on your hub.

    For a point where connections meet and power only passes through, such as a switchboard or a DC bus, use a [junction](junction.md) instead.

!!! danger "Attach a node only through a limiting, priced connection"

    A node that can produce or consume power does so without any limit or price of its own.
    Connect it to the rest of your network only through [connections](connections.md) that set a power limit and a price.
    Connections are one-way, so a node that both produces and consumes power needs a limited, priced connection in each direction.
    Without them, the optimizer can create free power from a source node or dump power for free into a sink node, and the resulting plan will not be physically meaningful.

## Configuration

| Field                       | Type    | Required | Default | Description                              |
| --------------------------- | ------- | -------- | ------- | ---------------------------------------- |
| **[Name](#name)**           | String  | Yes      | -       | Unique identifier for this node          |
| **[Is Source](#is-source)** | Boolean | No       | false   | Whether node can produce unlimited power |
| **[Is Sink](#is-sink)**     | Boolean | No       | false   | Whether node can consume unlimited power |

See [Where values are measured](../measurement-points.md) for the convention HAEO uses for where limits, prices, and reported power apply.

## Name

Unique identifier for this node within your HAEO configuration.
Used to identify the node in connection endpoints.

Choose descriptive names based on what the node represents: "Generator", "Neighbor Supply", "Dump Load"

## Is Source

Whether this node can produce power.
When on, the node can supply any amount of power that flows out through its connections.

**Default**: off (node cannot produce power)

## Is Sink

Whether this node can consume power.
When on, the node can absorb any amount of power that flows in through its connections.

**Default**: off (node cannot consume power)

### Source and Sink Combinations

The combination of `is_source` and `is_sink` determines the node's behavior:

**Source Only** (`is_source=true, is_sink=false`):

- Node can produce power that flows out through connections
- Cannot accept power from connections
- Useful for modeling a power source without a dedicated generation or grid element

**Sink Only** (`is_source=false, is_sink=true`):

- Node can accept power that flows in through connections
- Cannot produce power
- Useful for modeling a power sink without a dedicated consumption element

**Bidirectional** (`is_source=true, is_sink=true`):

- Node can both produce and consume power
- Useful for modeling a flexible power exchange point
- Similar to a grid element, but the connections to and from it carry the limits and prices

**Neither** (`is_source=false, is_sink=false`):

- Power must balance, exactly like a [junction](junction.md)
- Useful when you want to switch the node's role on and off at runtime through its input entities
- If the role never changes, use a junction instead

!!! info "Node role and power policies"

    Source/sink switches also determine how [power policies](../../modeling/tagged-power.md) follow energy through the node.
    A node that can produce or consume power can be chosen as a policy source or destination.
    Sinks terminate a policy's provenance — a `source=X → destination=Y` rule cannot see past an intermediate sink.
    See [Node roles and policy scope](../../modeling/tagged-power.md#node-roles-and-policy-scope) for the full rules.

## Configuration Example

A backup generator modeled as a source node:

| Field         | Value     |
| ------------- | --------- |
| **Name**      | Generator |
| **Is Source** | On        |
| **Is Sink**   | Off       |

Then add a connection from "Generator" to your switchboard with a maximum power matching the generator rating and a price matching its fuel cost per kWh.

!!! warning "Deleting nodes"

    If you delete a node element, you must update all connections that reference it.
    Connections cannot have endpoints that don't exist.

### Input Entities

Each configuration option creates a corresponding input entity in Home Assistant.
Input entities appear as Switch entities with the `config` entity category.
Because they are entities, you can switch a node's role at runtime, for example from an automation.

| Input                     | Description                              |
| ------------------------- | ---------------------------------------- |
| `switch.{name}_is_source` | Whether node can produce unlimited power |
| `switch.{name}_is_sink`   | Whether node can consume unlimited power |

Input entities include a `forecast` attribute showing values for each optimization period.
See the [Input Entities developer guide](../../developer-guide/inputs.md) for details on input entity behavior.

## Sensors Created

### Sensor Summary

A Node element creates 1 device in Home Assistant with the following sensors.

| Sensor                                                       | Unit   | Description                     |
| ------------------------------------------------------------ | ------ | ------------------------------- |
| [`sensor.{name}_power_balance_shadow_price`](#power-balance) | \$/kWh | Local energy price at this node |

### Power Balance

Displayed as "Power balance shadow price".
The marginal cost or value of power at this node.
It is interpreted the same way as the [junction power balance sensor](junction.md#power-balance).
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

---

All sensors include a `forecast` attribute containing future optimized values for upcoming periods.

## Troubleshooting

**Unexpectedly cheap or profitable plan**: A source or sink node is connected without a power limit or price.
Add a limit and a price to every connection to or from the node.

**Infeasible optimization**: Check all elements connected, connection directions correct, limits not too restrictive.

## Next steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Configure connections**

    ---

    Set the limits and prices on the connections to your node.

    [:material-arrow-right: Connections guide](connections.md)

- :material-source-branch:{ .lg .middle } **Junctions**

    ---

    Add a point where connections meet and power only passes through.

    [:material-arrow-right: Junction guide](junction.md)

- :material-math-integral:{ .lg .middle } **Node modeling**

    ---

    Understand the source, sink, and power balance formulation at nodes.

    [:material-arrow-right: Node modeling](../../modeling/device-layer/node.md)

</div>
