# Elements

Elements are the core building blocks of HAEO's energy network model.
They represent physical devices that produce, consume, store, or route power.

## Kinds of element

Elements come in two kinds:

- **Network elements** produce, consume, or store power themselves.
    Connections join them, and each balances its own power and carries tags for [tagged power](../../tagged-power.md).
- **Flow readers** produce and consume nothing.
    They read the planned flows of other elements to price or constrain them, so they are added once those flows exist.

Each element type has its own page describing its variables, constraints, and costs.

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

## Next steps

<div class="grid cards" markdown>

- :material-battery-charging:{ .lg .middle } **Battery**

    ---

    Energy storage with SOC dynamics.

    [:material-arrow-right: Battery model](battery.md)

- :material-timer-outline:{ .lg .middle } **Deferrable load**

    ---

    Energy delivered within scheduled events.

    [:material-arrow-right: Deferrable load model](deferrable_load.md)

- :material-source-branch:{ .lg .middle } **Node**

    ---

    Sources, sinks, and junction points.

    [:material-arrow-right: Node model](node.md)

- :material-shield-check:{ .lg .middle } **Buffer**

    ---

    Energy or empty space batteries keep over a window.

    [:material-arrow-right: Buffer model](buffer.md)

- :material-cash-multiple:{ .lg .middle } **Policy pricing**

    ---

    Policy prices applied to tagged power flows.

    [:material-arrow-right: Policy pricing model](policy_pricing.md)

- :material-connection:{ .lg .middle } **Connections**

    ---

    Power flow paths between elements.

    [:material-arrow-right: Connection types](../connections/index.md)

- :material-layers-outline:{ .lg .middle } **Device layer**

    ---

    How user-configured devices compose elements.

    [:material-arrow-right: Device layer](../../device-layer/index.md)

</div>
