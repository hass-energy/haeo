# Architecture

HAEO follows Home Assistant integration patterns with specialized optimization components.
This guide focuses on HAEO-specific architecture.
For Home Assistant fundamentals, see the [Home Assistant developer documentation](https://developers.home-assistant.io/).

## System Overview

```mermaid
graph TD
    CF[Config Flow] --> CE[Config Entry]
    CE --> Coord[Coordinator]
    Coord --> Loaders[Data Loaders]
    Coord --> Builder[Network Builder]
    Builder --> Model[Network Model]
    Model --> Optimizer[HiGHS Optimizer]
    Optimizer --> Results[Results]
    Results --> Sensors[Sensors]

    style Coord fill:#FFE4B5
    style Optimizer fill:#90EE90
```

## Core Components

### Config Flow (`config_flow.py`, `flows/`)

User-facing configuration via the Home Assistant UI.
The hub flow creates the main entry and exposes additional flows so users can add and manage elements without leaving the standard interface.

See the Home Assistant documentation for the underlying patterns:

- [Config Entries](https://developers.home-assistant.io/docs/config_entries_index/)
- [Config Flow Handler](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)
- [Data Entry Flow](https://developers.home-assistant.io/docs/data_entry_flow_index/)

### Coordinator (`coordinator.py`)

Central manager scheduling optimization cycles (default 5 min), loading data, building network, running optimization, distributing results.
Each hub entry creates one coordinator instance.

See the [DataUpdateCoordinator documentation](https://developers.home-assistant.io/docs/integration_fetching_data/#coordinated-single-api-poll-for-data-for-all-entities) for the base pattern.
HAEO's coordinator gathers sensor values, assembles the optimization network, runs the optimizer in an executor, and pushes the results back to the entities.
It listens for element additions or removals and triggers a refresh whenever the underlying data changes.

### Data loaders (`data/`)

Data loaders translate configuration into time series the model can consume.
They validate values during the config flow and fetch real sensor data at runtime, including support for common forecast formats.
Keep new loaders focused on a single responsibility and reuse the shared parser utilities where possible.

### Network Builder

Creates optimization model from config:

- Instantiates element objects (Battery, Grid, etc.)
- Creates Connection objects
- Builds Network container
- Validates structure

### Network Model (`model/`)

LP representation using PuLP:

- **Element**: Base class for all model elements with power/energy variables
- **Battery**: Storage with charge/discharge power, SOC constraints
- **Grid**: Import/export with optional limits and pricing
- **Photovoltaics**: Solar generation with optional curtailment
- **ConstantLoad, ForecastLoad**: Consumption elements
- **Node**: Virtual balance point enforcing Kirchhoff's law
- **Connection**: Power flow path with optional min/max limits
- **Network**: Container with `optimize()`, `cost()`, and `constraints()` methods

### Optimization

Uses the HiGHS linear programming solver via PuLP to solve the energy optimization problem.
Minimizes cost while respecting all constraints, returning optimal cost and decision variable values.

### Sensors (`sensors/`)

Sensor entities expose optimization outputs through standard Home Assistant constructs.
Separate modules handle network-level metrics and per-element values, and every sensor carries a forecast attribute so downstream automations can look ahead.

See the Home Assistant documentation:

- [Entity creation](https://developers.home-assistant.io/docs/core/entity/)
- [Sensor entity](https://developers.home-assistant.io/docs/core/entity/sensor/)
- [Platform development](https://developers.home-assistant.io/docs/creating_platform_index/)
- [Device Registry](https://developers.home-assistant.io/docs/device_registry_index/)

### Model Architecture (`model/`)

Separate subsystem implementing the optimization model:

**Design principles**:

- Pure Python linear programming using PuLP
- Elements generate their own variables and constraints
- Network assembles elements and runs optimization
- No Home Assistant dependencies in model layer

**Key components**:

- `Element`: Base class with power/energy variable patterns
- Entity classes: Battery, Grid, Photovoltaics, Loads, Node
- `Connection`: Power flow with limits
- `Network`: Container with `optimize()` method

## Code Organization

The integration lives under `custom_components/haeo/` and follows Home Assistant layout conventions.
Rather than documenting every file, focus on how the major areas collaborate:

- **Entry points**: `__init__.py`, `config_flow.py`, and `coordinator.py` bootstrap the integration, collect user input, and run optimizations on schedule.
- **Flows (`flows/`)**: Houses hub, element, and options flows; each submodule owns the UI schema for a related group of entries.
- **Data layer (`data/`)**: Loader modules turn Home Assistant sensors and forecasts into normalized time series for the optimizer.
- **Model (`model/`)**: Pure Python optimization layer composed of elements, connections, and network orchestration.
- **Metadata (`elements/` and `schema/`)**: Describe configuration defaults, validation, and runtime metadata for every element type.
- **Presentation (`sensors/`)**: Builds coordinator entities and sensor platforms that publish optimization results back to Home Assistant.
- **Translations (`translations/`)**: Provides user-facing strings for config flows and entity names.

## Extension Points

### Adding Element Types

1. **Create model class** in `model/`:

    - Inherit from `Element`
    - Define power/energy variables
    - Implement `cost()` and `constraints()` methods

2. **Add element metadata** in `elements/`:

    - `*ConfigSchema`: For config flow validation
    - `*ConfigData`: For runtime with loaded values
    - Define field metadata using annotations

3. **Register element type** in `elements/__init__.py`:

    - Add to `ELEMENT_TYPES` mapping

4. **Create config flow** in `flows/elements/`:

    - Inherit from appropriate base
    - Implement validation and schema generation

5. **Update translations** in `translations/en.json`:

    - Add device and selector entries

6. **Write tests**:

    - Model element tests in `tests/model/test_elements.py`
    - Test data in `tests/model/test_data/`
    - Config flow tests in `tests/flows/`
    - Integration tests

### Custom Field Types

Extend `schema/fields.py`:

- Create new `FieldMeta` subclass
- Define validation schema
- Implement loader logic
- Register with field type system

## Related Documentation

- [Coordinator Guide](coordinator.md)
- [Energy Models](energy-models.md)
- [Testing](testing.md)
