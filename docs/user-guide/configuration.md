# Configuration

This guide explains how to configure your first HAEO energy network using the Home Assistant UI.

For more details on Home Assistant integration setup, see the [Home Assistant integration setup guide](https://www.home-assistant.io/getting-started/integration/).

## Overview

HAEO configuration happens entirely through Home Assistant's UI. You'll:

1. Create a **Hub** (the main integration entry coordinating optimization)
2. Add **Element Entries** (batteries, grids, solar, loads)
3. Add **Connection Entries** (defining how energy flows between elements)

## Creating Your First Hub

### Add the integration

1. Navigate to **Settings** → **Devices & Services**
2. Click the **Add Integration** button (+ in bottom right)
3. Search for **HAEO** or **Home Assistant Energy Optimization**
4. Click on it to start the configuration flow

### Configure hub settings

The hub configuration form includes these fields:

#### Name

A unique name for your energy hub (for example, "Home Energy System").

!!! tip "Multiple Hubs"

    You can create multiple separate hubs for distinct energy systems (separate buildings, testing configurations, different optimization strategies).
    Each hub manages its own set of element and connection entries independently.

#### Horizon hours

The optimization time horizon in hours (1-168).

Choose a horizon that matches the length of your forecasts so the optimizer can see the same window of data.
Set at least 48 hours whenever forecasts support it because that lets batteries plan a full charge and discharge cycle with awareness of the next day's demand.
Extending beyond 48 hours only helps if your battery capacity can sustain useful energy decisions over that period.

#### Period minutes

The time resolution for optimization in minutes (1-60).

Set the period to match the resolution of your most important sensor or price input whenever possible.
Shorter periods give finer control but increase solve time.
If optimizations feel slow, increase the period before reducing the horizon.

Click **Submit** to create your hub.

## Adding Elements

After creating your hub, add elements to represent your devices through the Home Assistant UI.

1. Navigate to **Settings** → **Devices & Services**
2. Find your **HAEO** hub integration
3. Click on the hub to open its details page
4. Click **Add Entry**
5. Choose the element type you want to add
6. Fill in the configuration fields
7. Click **Submit** to create the element

!!! note "Network entry"

    A network entry appears automatically when you set up your hub.
    It provides optimization sensors for the overall system and does not require manual configuration.

### Available element types

| Element Type      | Description                      | Use Case                      |
| ----------------- | -------------------------------- | ----------------------------- |
| **Battery**       | Energy storage with SOC tracking | Home batteries, EV as storage |
| **Grid**          | Bi-directional grid connection   | Main grid, separate meters    |
| **Photovoltaics** | Solar generation                 | Rooftop solar, ground-mount   |
| **Constant Load** | Fixed power loads                | Base load, always-on devices  |
| **Forecast Load** | Variable loads with forecasts    | Household consumption         |
| **Net**           | Virtual power balance node       | Grouping connection points    |

See the [elements overview](elements/index.md) for detailed configuration guides for each type.

## Defining Connections

Connections define how energy flows between elements.
Add them from the same hub page as elements by selecting **Connection** from the element type list.

### Example network topology

```mermaid
graph LR
    Grid[Grid] <-->|Bi-directional| Net[Net]
    Net <--> Battery[Battery]
    Solar[Solar] --> Net
    Net --> Load[Load]
```

This requires these connections:

1. Grid ↔ Net (bi-directional)
2. Battery ↔ Net (bi-directional)
3. Solar → Net (one-way)
4. Net → Load (one-way)

See the [Connections guide](elements/connections.md) for detailed information and examples.

## Viewing Configuration

### Integration page

On the HAEO integration page, you'll see:

- **Network device**: Represents your entire energy system
- **Network sensors**: Optimization status, cost, duration
- **Element sensors**: Power, energy, SOC for each configured element

Each sensor includes forecast attributes with future timestamped values.
See the [Understanding Results guide](optimization.md) for details on interpreting sensor values.

## Modifying Configuration

### Editing elements and connections

Use the **Configure** button on each entry in **Settings** → **Devices & Services** to edit parameters.
Changes trigger a new optimization.

### Removing elements and connections

Use the three-dot menu on each entry to delete it.
The hub automatically adjusts optimization for remaining elements.

!!! danger "Cascade effects"

    Removing elements used in connections may affect network connectivity.

### Editing hub settings

Click **Configure** on the hub entry to modify horizon hours, period minutes, or optimizer.
Changes trigger immediate re-optimization with the new parameters.

## Best Practices

### Start simple

Begin with a minimal configuration (Grid + Battery + Connection), verify optimization works, then add complexity gradually.

### Use meaningful names

Choose descriptive element names using friendly, readable format:

- ✅ "Main Battery", "Grid Import", "Rooftop Solar"
- ❌ "Battery1", "Thing", "Device"

### Monitor performance

Watch optimization duration in the sensor.
If it takes too long, increase period minutes or reduce horizon hours.
See [performance considerations](optimization.md#performance-considerations) for more details.

## Next Steps

Use these resources to expand your configuration and understand the results.

<div class="grid cards" markdown>

- :material-cog-transfer-outline:{ .lg .middle } __Configure individual elements__

    Set up batteries, grids, photovoltaics, and loads with detailed guidance.

    [:material-arrow-right: Element guides](elements/index.md)

- :material-view-dashboard-outline:{ .lg .middle } __Understand optimization outputs__

    Interpret HAEO sensor data and forecast attributes.

    [:material-arrow-right: Optimization overview](optimization.md)

- :material-play-circle-outline:{ .lg .middle } __Review a complete example__

    Follow a full walkthrough that combines all configuration steps.

    [:material-arrow-right: Sigenergy example](examples/sigenergy-system.md)

</div>
