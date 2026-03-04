# Adapter layer

The adapter layer transforms Device Layer elements into Model Layer elements and maps optimization outputs back to user-friendly device outputs.
This separation enables composition flexibility where a single configuration creates multiple model elements and devices.

## Purpose

HAEO separates user configuration from optimization modeling through distinct layers:

- **Device Layer**: User-configured elements (Battery, Grid, Solar, Load, Node, Connection) with Home Assistant sensor integration
- **Model Layer**: Mathematical building blocks forming the linear programming problem
- **Adapter Layer**: Transformation logic connecting these layers

This architecture enables:

- **Composition flexibility**: One Device Layer element creates multiple Model Layer elements
- **Output aggregation**: Model outputs map to multiple devices with user-friendly sensor names
- **Future extensibility**: Foundation for composite elements that group multiple devices

## Transformation Flow

```mermaid
graph LR
    subgraph "Device Layer"
        Config[User Configuration]
    end

    subgraph "Adapter Layer"
        Create["model_elements()"]
        Map["outputs()"]
    end

    subgraph "Model Layer"
        Model[Model Elements]
        Results[Optimization Results]
    end

    subgraph "Home Assistant"
        Devices[Devices & Sensors]
    end

    Config --> Create
    Create --> Model
    Model --> Results
    Results --> Map
    Map --> Devices
```

The adapter layer provides two transformation functions per element type:

**Configuration → Model** (`model_elements`): Transforms user configuration into model element specifications.
Called during network construction before optimization.
The adapter returns `ModelElementConfig` dictionaries with a discriminated `element_type`.
Use model-layer element type constants from `custom_components/haeo/core/model/elements/__init__.py`.

**Model → Devices** (`outputs`): Transforms optimization results into device-specific outputs with user-friendly names.
Called after optimization to populate sensors.

## Element Composition Patterns

### One-to-Many Model Elements

Most Device Layer elements create multiple Model Layer elements:

| Device Element | Model Elements Created   |
| -------------- | ------------------------ |
| Battery        | `battery` + `connection` |
| Grid           | `node` + `connection`    |
| Solar          | `node` + `connection`    |
| Load           | `node` + `connection`    |
| Node           | `node` only              |
| Connection     | `connection` only        |

Implicit connections (created by Battery, Grid, PV, Load) link the element to its configured target node.
The connection carries operational parameters (power limits, efficiency, pricing) from the device configuration.

### One-to-Many Devices

Some Device Layer elements produce multiple devices in Home Assistant:

**Battery**: Creates up to 4 devices based on SOC region configuration:

- Aggregate device (always): Total power, energy, SOC
- Undercharge device (optional): Region-specific metrics
- Normal device (optional): Region-specific metrics
- Overcharge device (optional): Region-specific metrics

Other elements create a single device matching their configuration.

### Sub-element Naming

When adapters create multiple model elements or devices, they use a naming convention:

- Main element: `{name}` (e.g., `Battery`)
- Sub-elements: `{name}:{subname}` (e.g., `Battery:connection`, `Battery:undercharge`)

This prevents naming collisions and groups related components visually.

## Adding New Element Types

To add a new Device Layer element:

1. Define schema in `core/schema/elements/{element_type}.py` with `ConfigSchema`, `ConfigData`, and `DEFAULTS`
2. Implement adapter in `core/adapters/elements/{element_type}.py` with `available()`, `inputs()`, `model_elements()`, `outputs()`
3. Implement config flow in `flows/elements/{element_type}.py`
4. Register `ElementAdapter` in `elements/__init__.py` `ELEMENT_TYPES` dictionary
5. Add translations in `translations/en.json`
6. Write tests colocated with source (adapter tests in `core/adapters/elements/tests/`, flow tests in `flows/elements/tests/`)

See existing adapter modules in [`custom_components/haeo/core/adapters/elements/`](https://github.com/hass-energy/haeo/tree/main/custom_components/haeo/core/adapters/elements) for implementation patterns.

## Integration Points

The adapter layer integrates at two points in HAEO's execution:

**Network construction**: [`coordinator/network.py`](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/coordinator/network.py) calls `model_elements()` for each configured element to build the optimization network.
The `create_network()` function assembles all element specifications and adds them to the network.

**Output processing**: [`coordinator/coordinator.py`](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/coordinator/coordinator.py) calls `outputs()` after optimization to transform results into device sensor values.

## Future: Composite Elements

The adapter architecture supports future composite elements that group multiple Device Layer elements:

- **Virtual Power Plant**: Multiple batteries and solar systems as a single unit
- **Building**: Aggregated loads and generation for a location
- **Pre-configured networks**: Complete system templates

Composite adapters would create nested element structures and aggregate their outputs, presenting a unified interface to users while maintaining full optimization capability.

## Next Steps

<div class="grid cards" markdown>

- :material-chart-line:{ .lg .middle } **Modeling documentation**

    ---

    Understand the Model Layer mathematical formulation.

    [:material-arrow-right: Network optimization](../modeling/index.md)

- :material-file-document:{ .lg .middle } **Element configuration**

    ---

    User guide for Device Layer elements.

    [:material-arrow-right: Elements overview](../user-guide/elements/index.md)

- :material-database:{ .lg .middle } **Data loading**

    ---

    How sensor data flows into configuration.

    [:material-arrow-right: Data loading guide](data-loading.md)

</div>
