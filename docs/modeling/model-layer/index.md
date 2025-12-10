# Model Layer Elements

Model Layer elements are the mathematical building blocks of HAEO's linear programming formulation.
These elements define decision variables, constraints, and cost contributions that the optimizer uses to find the optimal energy schedule.

## Overview

HAEO uses three Model Layer element types to represent all energy system behaviors:

| Model Element                    | Purpose                                          |
| -------------------------------- | ------------------------------------------------ |
| **[Battery](battery.md)**        | Energy storage with multi-section SOC tracking   |
| **[SourceSink](source-sink.md)** | Power source, sink, or junction point            |
| **[Connection](connection.md)**  | Bidirectional power flow with limits and pricing |

## Design Philosophy

The Model Layer provides a minimal set of mathematical primitives that combine to represent complex behaviors:

**Composition over complexity**: Rather than creating specialized models for each device type, Device Layer elements compose these simple building blocks with different parameter mappings.

**Separation of concerns**: The Model Layer handles pure optimization mathematics.
Device-specific behavior (sensor integration, output naming, multi-device creation) lives in the Device Layer.

**Extensibility**: New device types can often be created by composing existing Model Layer elements with different parameter mappings, without new mathematical formulations.

## Model Aggregation

The complete optimization problem is built by combining contributions from all Model Layer elements:

**Decision variables**: Each element introduces variables representing its behavior (power flows, energy states).
The complete variable set is the union of all element variables.

**Constraints**: Each element contributes constraints governing its operation.
The complete constraint set is the union of all element constraints plus network-wide power balance.

**Objective function**: Each element may contribute cost terms.
The total objective is the sum of all element cost contributions.

## Next Steps

<div class="grid cards" markdown>

- :material-battery-charging:{ .lg .middle } **Battery model**

    ---

    Energy storage with multi-section SOC tracking.

    [:material-arrow-right: Battery formulation](battery.md)

- :material-power-plug:{ .lg .middle } **SourceSink model**

    ---

    Unified model for sources, sinks, and junctions.

    [:material-arrow-right: SourceSink formulation](source-sink.md)

- :material-connection:{ .lg .middle } **Connection model**

    ---

    Bidirectional power flow with constraints.

    [:material-arrow-right: Connection formulation](connection.md)

</div>
