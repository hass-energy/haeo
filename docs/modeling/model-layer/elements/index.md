# Elements

Elements are the core building blocks of HAEO's energy network model.
They represent physical devices that produce, consume, store, or route power.

## Element types

HAEO provides two element types that serve different roles in the network:

**[Battery](battery.md)**:
Energy storage with state of charge tracking.
Models capacity, charge/discharge flows, and SOC constraints.

**[Node](node.md)**:
Power sources, sinks, and junction points.
Enforces power balance (Kirchhoff's law) at connection points.

## Common characteristics

All elements share these properties:

- **Power variables**: Track power flows at each time step
- **Constraints**: Define operational limits and physical laws
- **Outputs**: Provide optimization results for sensors

Elements connect to each other through [Connection](../connections/index.md) objects, which handle power transfer between elements.

## Design philosophy

Elements are intentionally simple mathematical primitives.
Complex device behavior (multi-section batteries, cost incentives, efficiency losses) is achieved by:

1. Composing multiple elements together
2. Configuring [Connections](../connections/index.md) with appropriate parameters
3. Mapping user configuration through the [Device Layer](../../device-layer/index.md)

This separation keeps the Model Layer focused on optimization mathematics while the Device Layer handles user-facing complexity.

## Next Steps

<div class="grid cards" markdown>

- :material-battery-charging:{ .lg .middle } **Battery model**

    ---

    Energy storage with SOC tracking and capacity constraints.

    [:material-arrow-right: Battery formulation](battery.md)

- :material-power-plug:{ .lg .middle } **Node model**

    ---

    Power balance points for sources, sinks, and junctions.

    [:material-arrow-right: Node formulation](node.md)

- :material-connection:{ .lg .middle } **Connections**

    ---

    Power flow paths between elements.

    [:material-arrow-right: Connection types](../connections/index.md)

</div>
