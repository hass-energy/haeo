# Model Layer

The Model Layer provides mathematical building blocks for HAEO's linear programming formulation.
Elements at this layer define decision variables, constraints, and cost contributions that the optimizer uses to find optimal energy schedules.

## Architecture

The Model Layer uses a minimal set of mathematical primitives that compose to represent complex energy system behaviors.
These primitives are organized into two categories:

**[Elements](elements/index.md)**: Represent physical devices that produce, consume, or store power.
Elements define their own state (energy, power) and constraints (capacity, balance).

**[Connections](connections/index.md)**: Model power flow paths between elements.
Connections handle power transfer, efficiency losses, limits, and pricing.

This separation enables flexible network topologies where the same element types can be connected in different ways.

## Design principles

**Composition over complexity**:
Rather than creating specialized models for each device type, Device Layer elements compose simple mathematical primitives with different parameter mappings.

**Separation of concerns**:
The Model Layer handles pure optimization mathematics.
Device-specific behavior (sensor integration, output naming, multi-device creation) lives in the [Device Layer](../device-layer/index.md).

**Extensibility**:
New device types can often be created by composing existing Model Layer elements with different parameter mappings, without requiring new mathematical formulations.

## Optimization problem construction

The complete optimization problem aggregates contributions from all Model Layer elements.

**Decision variables**:
Each element introduces variables representing its behavior (power flows, energy states).
The complete variable set is the union of all element variables.

**Constraints**:
Each element contributes constraints governing its operation.
The complete constraint set is the union of all element constraints plus network-wide power balance.

**Objective function**:
Each element may contribute cost terms.
The total objective is the sum of all element cost contributions.

## Next Steps

<div class="grid cards" markdown>

-   :material-battery-charging:{ .lg .middle } **Elements**

    ---

    Battery and Node model elements for storage and power balance.

    [:material-arrow-right: Element types](elements/index.md)

-   :material-connection:{ .lg .middle } **Connections**

    ---

    Power flow paths with efficiency, limits, and pricing.

    [:material-arrow-right: Connection types](connections/index.md)

-   :material-layers:{ .lg .middle } **Device Layer**

    ---

    How user configuration maps to Model Layer elements.

    [:material-arrow-right: Device Layer](../device-layer/index.md)

</div>
