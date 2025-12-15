# Elements

Elements are the building blocks of your HAEO energy network.
Each element represents a physical device or logical component in your energy system.

## Elements and Devices

When you configure an element, HAEO may create multiple devices in Home Assistant.
Elements can create one or more devices depending on their configuration.
Each device has its own set of sensors showing optimization results.

This composition allows HAEO to represent complex physical systems with multiple operational modes while keeping configuration simple.
See individual element pages for which devices and sensors each element creates.

!!! info "Elements vs Home Assistant Entities"

    In HAEO documentation:

    - **Element** = A component you configure (battery, grid, solar, etc.)
    - **Device** = A Home Assistant device created by an element (may be one or more per element)
    - **Sensor** = A Home Assistant sensor entity on a device

    See individual element pages for which devices and sensors each element creates.

For the mathematical details of how elements are modeled, see the [Modeling Documentation](../../modeling/index.md).

## How Elements Work Together

Elements work together once you connect them to match your real-world wiring.
HAEO balances available energy, expected consumption, and any limits you set so the total system stays within bounds.
In a typical home system, solar may feed a common node, the grid can import or export, and a battery shifts energy between time periods.

Example layout:

```mermaid
graph TD
    Solar[Photovoltaics] --> Net[Node]
    Grid[Grid] <--> Net
    Net --> Battery[Battery]
    Battery --> Load[Load]
```

This layout lets HAEO decide when to store solar, rely on the grid, or draw from a battery while keeping every connection within the limits you configured.
See the [modeling documentation](../../modeling/index.md) for the underlying mathematics.

## Configuration Approach

When configuring elements:

1. **Start simple**: Begin with just a grid and one other element
2. **Add gradually**: Introduce complexity one element at a time
3. **Verify each step**: Check that optimization produces reasonable results
4. **Use realistic values**: Base constraints on actual device specifications

## Next Steps

Explore detailed configuration for each element type:

<div class="grid cards" markdown>

- :material-battery:{ .lg .middle } __Battery configuration__

    Energy storage with SOC tracking and efficiency modeling.

    [:material-arrow-right: Battery guide](battery.md)

- :material-power-plug:{ .lg .middle } __Grid configuration__

    Import/export with dynamic or fixed pricing.

    [:material-arrow-right: Grid guide](grid.md)

- :material-weather-sunny:{ .lg .middle } __Photovoltaics configuration__

    Solar generation with curtailment options.

    [:material-arrow-right: Photovoltaics guide](photovoltaics.md)

- :material-gauge:{ .lg .middle } __Load configuration__

    Power consumption with constant or forecast-based patterns.

    [:material-arrow-right: Load guide](load.md)

- :material-source-branch:{ .lg .middle } __Node configuration__

    Virtual power balance nodes.

    [:material-arrow-right: Node guide](node.md)

</div>
