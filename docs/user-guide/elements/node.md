# Node

Virtual balance points enforcing power conservation (Kirchhoff's law).

## Configuration

| Field             | Type   | Required | Default | Description                     |
| ----------------- | ------ | -------- | ------- | ------------------------------- |
| **[Name](#name)** | String | Yes      | -       | Unique identifier for this node |

## Name

Unique identifier for this node within your HAEO configuration.
Used to identify the node in connection endpoints.

Choose descriptive names based on electrical location: "Main Node", "AC Panel", "DC Bus", "Home Circuit"

## Purpose

Nodes are connection hubs where power balance is enforced:

$$
\text{Power In} = \text{Power Out}
$$

Nodes are not physical devices - they represent electrical junctions where Kirchhoff's current law applies.

!!! tip "Key insight"

    All elements (batteries, grids, loads, etc.) function as nodes in the network.
    Explicit Node elements are only needed when you want an additional connection point without any associated device.

## Use Cases

**Single node (simple)**: Central hub for all elements.

```mermaid
graph LR
    Grid<-->Node[Node]
    Solar-->Node
    Battery<-->Node
    Node-->Load

    class Node emphasis
```

Most residential systems use one node.

**Multiple nodes (complex)**: Separate AC/DC or hierarchical distribution.

```mermaid
graph LR
    Solar-->DC[DC Node]
    Battery<-->DC
    DC<-->|Inverter|AC[AC Node]
    Grid<-->AC
    AC-->Load

    class DC dc
    class AC ac
```

Hybrid inverter systems with separate buses.

## Configuration Example

Simple node for connecting elements:

| Field    | Value     |
| -------- | --------- |
| **Name** | Main Node |

Then connect elements to "Main Node" via connections.

!!! warning "Deleting nodes"

    If you delete a node element, you must update all connections that reference it.
    Connections cannot have endpoints that don't exist.

## Sensors Created

Nodes are virtual balance points with one shadow price sensor.

| Sensor                                                    | Unit  | Description                     |
| --------------------------------------------------------- | ----- | ------------------------------- |
| [`sensor.{name}_node_power_balance`](#node-power-balance) | \$/kW | Local energy price at this node |

### Node Power Balance

The marginal cost or value of power at this specific node in the network.
See the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

This shadow price represents the "local spot price" for energy at this connection point.
It shows how much the total system cost would change if you could inject or extract 1 kW of power at this node.

**Interpretation**:

- **Positive value**: Represents the cost of power at this node
    - Higher values indicate expensive power (e.g., importing during peak prices)
    - Shows what you would save by reducing consumption or adding generation at this node
- **Negative value**: Represents surplus power at this node (uncommon)
    - Indicates more generation than consumption
    - Shows the value that could be captured by adding loads or storage at this node
- **Differences between nodes**: Reveal the economic value of power transfer between network locations
    - Larger differences indicate stronger incentive for power flow between nodes
    - Help identify valuable connection points in the network

**Example**: A value of 0.22 means power at this node costs \$0.22 per kW at this time period, reflecting the marginal cost to supply this location in the network.

**Note**: For physical power measurements, monitor connected entity sensors instead.
Nodes only provide shadow prices, not physical power flow data.

---

All sensors include a `forecast` attribute containing future optimized values for upcoming periods.

## Troubleshooting

**Infeasible optimization**: Check all elements connected, sufficient sources exist, connection directions correct, limits not too restrictive.

**Unexpected power flows**: Verify connection endpoints, review node names unique, check connection min/max power limits.

## Multiple Nodes

**Use when**:

- Physical separation (AC/DC buses in hybrid inverter systems)
- Intermediate limits (inverter capacity, feeder constraints)
- Hierarchical distribution (main panel and sub-panels)

**Configuration**: Create multiple node elements, link them with connections.

**Complexity**: Requires more configuration and adds more constraints, but accurately models real system architecture.

### Hybrid Inverter Example

For hybrid (AC/DC) inverter systems, use separate AC and DC nodes with a connection between them:

```mermaid
graph LR
    Battery[Battery] <--> DC[DC Node]
    Solar[Photovoltaics] --> DC
    DC <-->|Inverter| AC[AC Node]
    Grid[Grid] <--> AC
    AC --> Load[Load]
```

The **connection** between DC and AC nodes represents the inverter.
Set connection power limits to match the inverter rating.

| Connection        | Max Power                            |
| ----------------- | ------------------------------------ |
| DC Node → AC Node | Inverter output rating (e.g., 10 kW) |
| AC Node → DC Node | Inverter input rating (e.g., 10 kW)  |

See [Connections](connections.md) for detailed configuration guidance.

## Next Steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Configure connections**

    ---

    Learn how to connect elements using power flow connections.

    [:material-arrow-right: Connections guide](connections.md)

- :material-math-integral:{ .lg .middle } **Node modeling**

    ---

    Understand the power balance formulation at nodes.

    [:material-arrow-right: Node modeling](../../modeling/node.md)

- :material-chart-line:{ .lg .middle } **Understand optimization**

    ---

    See how power flows through nodes during optimization.

    [:material-arrow-right: Optimization results](../optimization.md)

</div>
