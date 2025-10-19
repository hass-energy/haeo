# Elements

Elements are the building blocks of your HAEO energy network.
Each element represents a physical device or logical component in your energy system.

!!! info "Elements vs Home Assistant Entities"

    In HAEO documentation:

    - **Element** = A component in your energy optimization (battery, grid, solar, etc.)
    - **Entity** = A Home Assistant sensor or device entity (e.g., `sensor.battery_power`)

    This page describes HAEO elements. Each element creates several Home Assistant entities (sensors).

## Element Types

HAEO supports several element types for modeling your energy system:

### **[Battery](battery.md)**

Energy storage with state of charge tracking, charge/discharge rates, and efficiency modeling.

### **[Grid](grid.md)**

Bi-directional grid connection for import/export with dynamic or fixed pricing.

### **[Photovoltaics](photovoltaics.md)**

Solar power generation with forecast integration and optional curtailment.

### **[Constant Load](constant-load.md)**

Fixed power consumption that doesn't vary over time.

### **[Forecast Load](forecast-load.md)**

Variable consumption based on forecast data.

### **[Node](node.md)**

Virtual power balance node for grouping connections and managing complex topologies.

### **[Connections](connections.md)**

Define how power flows between elements (technically connections are configuration, not elements, but grouped here for convenience).

## How Elements Work Together

Elements work together once you connect them to match your real-world wiring.
HAEO balances available energy, expected consumption, and any limits you set so the total system stays within bounds.
In a typical home system, solar may feed a common node, the grid can import or export, and a battery shifts energy between time periods.

Example layout:

```
Solar → Net ← Grid
         ↓
      Battery
         ↓
       Load
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

- :material-gauge:{ .lg .middle } __Constant load configuration__

    Fixed power consumption.

    [:material-arrow-right: Constant load guide](constant-load.md)

- :material-chart-timeline:{ .lg .middle } __Forecast load configuration__

    Variable consumption with forecasts.

    [:material-arrow-right: Forecast load guide](forecast-load.md)

- :material-source-branch:{ .lg .middle } __Node configuration__

    Virtual power balance nodes.

    [:material-arrow-right: Node guide](node.md)

</div>
