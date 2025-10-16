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

Elements are connected to form your energy network. The optimizer determines optimal power flow through each connection based on:

- Energy availability (solar generation, battery SOC)
- Costs (import/export prices, artificial costs for incentives)
- Constraints (power limits, battery capacity, connection limits)
- Forecast data (prices, generation, consumption)

For example, in a typical home system:

```
Solar → Net ← Grid
         ↓
      Battery
         ↓
       Load
```

The optimizer decides when to:

- Store solar in the battery vs export to grid
- Discharge battery vs import from grid
- Charge battery from grid during low-price periods

See the [modeling documentation](../../modeling/index.md) for mathematical details.

## Configuration Approach

When configuring elements:

1. **Start simple**: Begin with just a grid and one other element
2. **Add gradually**: Introduce complexity one element at a time
3. **Verify each step**: Check that optimization produces reasonable results
4. **Use realistic values**: Base constraints on actual device specifications

## Next Steps

Explore detailed configuration for each element type:

<div class="grid cards" markdown>

- [Battery Configuration](battery.md)

    Energy storage with SOC tracking and efficiency modeling.

- [Grid Configuration](grid.md)

    Import/export with dynamic or fixed pricing.

- [Photovoltaics Configuration](photovoltaics.md)

    Solar generation with curtailment options.

- [Constant Load Configuration](constant-load.md)

    Fixed power consumption.

- [Forecast Load Configuration](forecast-load.md)

    Variable consumption with forecasts.

- [Node Configuration](node.md)

    Virtual power balance nodes.

</div>
