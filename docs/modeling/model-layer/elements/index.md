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

- **Decision variables**: Track power flows at each time step
- **Parameters**: Define element behavior (capacities, limits, prices)
- **Constraints**: Define operational limits and physical laws
- **Cost contributions**: Optional terms added to the objective function
- **Outputs**: Provide optimization results for sensors

Elements connect to each other through [Connection](../connections/index.md) objects, which handle power transfer between elements.

### Constraint and cost aggregation

Each element declares the constraints it requires and any costs it contributes.
The network collects these declarations from all elements to form the complete optimization problem:

- **Constraint set**: $\mathcal{C}_e$ for element $e$
- **Cost contribution**: $\text{Cost}_e$ for element $e$

The network aggregates these into the complete problem (see [Model Layer overview](../index.md#declarative-constraint-aggregation)).

### Parameter updates

Element parameters can be updated between optimization runs without reconstructing the entire network.
When a parameter changes (such as an updated forecast or modified capacity), only the constraints that depend on that parameter are rebuilt.
This selective rebuilding enables efficient re-optimization when forecasts update frequently.

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
