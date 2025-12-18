# Device Layer Elements

Device Layer elements are the user-configured components that represent physical devices in your energy system.
Each Device Layer element composes one or more [Model Layer elements](../model-layer/index.md) to achieve its behavior.

## Overview

Device Layer elements transform user configuration into Model Layer elements.
Each element type composes one or more Model Layer elements to achieve its specific behavior.
See individual element pages for composition details.

## Composition Pattern

Device Layer elements use an adapter pattern to transform user configuration into Model Layer elements:

**Configuration → Model** (`create_model_elements`): Transforms user configuration into Model Layer element specifications.
Called during network construction before optimization.

**Model → Devices** (`outputs`): Transforms optimization results into device-specific outputs with user-friendly names.
Called after optimization to populate sensors.

## Implicit Connections

Many Device Layer elements create implicit connections automatically as part of their model composition.
These implicit connections simplify configuration—users specify their configuration needs, and the adapter handles connection creation with appropriate parameters.
See individual element pages for details on which connections are created.

## Sub-element Naming

When adapters create multiple model elements or devices, they use a colon-separated naming convention:

- Main element: `{name}` (e.g., `Battery`)
- Sub-elements: `{name}:{subname}` (e.g., `Battery:connection`, `Battery:undercharge`)

This prevents naming collisions and groups related components visually in Home Assistant.

## Next Steps

<div class="grid cards" markdown>

- :material-battery-charging:{ .lg .middle } **Battery**

    ---

    Energy storage modeling with SOC regions.

    [:material-arrow-right: Battery modeling](battery.md)

- :material-power-plug:{ .lg .middle } **Grid**

    ---

    Bidirectional utility connection with pricing.

    [:material-arrow-right: Grid modeling](grid.md)

- :material-swap-horizontal:{ .lg .middle } **Inverter**

    ---

    Bidirectional DC/AC power conversion with DC bus.

    [:material-arrow-right: Inverter modeling](inverter.md)

- :material-weather-sunny:{ .lg .middle } **Solar**

    ---

    Solar generation with optional curtailment.

    [:material-arrow-right: Solar modeling](solar.md)

- :material-gauge:{ .lg .middle } **Load**

    ---

    Power consumption modeling.

    [:material-arrow-right: Load modeling](loads.md)

</div>
