# Configuration Flow Development

Guide to HAEO's ConfigSubentry-based configuration flow implementation.

## Overview

HAEO uses Home Assistant's **ConfigSubentry architecture** where each element is managed as a subentry:

1. **Hub flow** (in `custom_components/haeo/flows/hub.py`): Creates the main hub entry and base subentries
2. **Element flows** (in `custom_components/haeo/flows/elements/<element>.py`): Create element ConfigSubentries using `ConfigSubentryFlow`
3. **Network subentry**: Automatically created representing the optimization network itself

This architecture follows Home Assistant's native [subentry pattern](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/).
Elements appear as subentries under the main hub in the UI with proper parent-child management.

For general information on config flows, see the [Home Assistant Config Flow documentation](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/) and [Data Entry Flow](https://developers.home-assistant.io/docs/data_entry_flow_index/).

### Architecture Benefits

- Native Home Assistant subentry UI integration
- Automatic parent-child relationship management
- Independent configuration of each element
- Proper device registry association via `config_subentry_id`
- Easy addition/removal through native UI
- No manual `parent_entry_id` tracking required

## Architecture

```mermaid
graph TD
    A[Add Integration] --> B{Entry Type?}
    B -->|First Time| C[Hub Flow]
    B -->|Hub Exists| D[Element Type Selection]
    C --> E[Optimization Settings]
    E --> F[Create Hub Entry]
    D --> G{Element Type}
    G -->|Battery| H[Battery Flow]
    G -->|Grid| I[Grid Flow]
    G -->|PV| J[PV Flow]
    G -->|Load| K[Load Flow]
    H --> L[Select Parent Hub]
    I --> L
    J --> L
    K --> L
    L --> M[Configure Element]
    M --> N[Create Subentry]
```

## Hub Flow

The hub flow creates the main integration entry that acts as a parent for element subentries and hosts the optimization coordinator.

### Hub entry structure

Hub entries are identified by the presence of `integration_type: "hub"` in their data.
Optimization settings are stored in `data` under section keys, not in `options`.

```python
{
    "entry_id": "abc123...",
    "domain": "haeo",
    "title": "Home Energy System",
    "data": {
        "integration_type": "hub",  # Marker to identify hub entries
        "common": {
            "name": "Home Energy System",
            "horizon_preset": "custom",
        },
        "tiers": {
            "tier_1_count": 5,
            "tier_1_duration": 1,
            "tier_2_count": 11,
            "tier_2_duration": 5,
            "tier_3_count": 46,
            "tier_3_duration": 30,
            "tier_4_count": 48,
            "tier_4_duration": 60,
        },
        "advanced": {
            "advanced_mode": False,
            "debounce_seconds": 30,
        },
        "record_forecasts": False,
    },
}
```

Optimization settings are stored in `data` (user-editable), alongside the hub marker.
The hub flow implementation is in `custom_components/haeo/flows/hub.py`.
The form uses sectioned schemas (`common`, `advanced`) and an optional `custom_tiers` step when users select a custom planning horizon.

### Key implementation points

- Hub flow uses a standard config flow pattern with a user step and optional custom tiers step
- Prevents duplicate hub names by checking existing entries
- Stores optimization settings in `data` sections so options flow can update them in-place
- Hub marker in `data` allows coordinator to identify hub entries

## Element Flows

Element subentries are created through separate config flows, one per element type.
All element flows inherit from a common base class that handles parent hub selection and entry creation.

### Element entry structure

Element entries are stored as subentries under the hub.
Element configuration is sectioned, with optional sections only present when configured.

```python
{
    "entry_id": "def456...",
    "domain": "haeo",
    "title": "Home Battery",
    "data": {
        "element_type": "battery",
        "common": {
            "name": "Home Battery",
            "connection": "Main Bus",
        },
        "storage": {
            "capacity": 13.5,
            "initial_charge_percentage": 50.0,
        },
        "limits": {
            "min_charge_percentage": 10.0,
            "max_charge_percentage": 90.0,
        },
        "power_limits": {
            "max_power_source_target": 5.0,
            "max_power_target_source": 5.0,
        },
        "pricing": {
            "price_source_target": 0.02,
            "price_target_source": 0.01,
        },
        "efficiency": {
            "efficiency_source_target": 95.0,
            "efficiency_target_source": 95.0,
        },
        "partitioning": {
            "configure_partitions": True,
        },
        "undercharge": {
            "percentage": 5.0,
            "cost": 1.5,
        },
        "overcharge": {
            "percentage": 95.0,
            "cost": 1.0,
        },
    },
}
```

### Base element flow pattern

All element flows use `ElementFlowMixin` which provides:

- Entry creation with proper subentry linkage
- Duplicate prevention
- Standard error handling

The element flow mixin is in `custom_components/haeo/flows/element_flow.py`.

### Connection endpoint filtering

Connection elements require selecting source and target endpoints from other configured elements.
The element flow filters available elements based on connectivity level and Advanced Mode setting.

Each element type in the `ELEMENT_TYPES` registry defines a connectivity level that controls when it appears in connection selectors.
The `ConnectivityLevel` enum has three values:

- **`ALWAYS`**: Always shown in connection selectors
- **`ADVANCED`**: Only shown when Advanced Mode is enabled
- **`NEVER`**: Never shown in connection selectors

This filtering ensures connection endpoints are appropriate for the user's configuration level.
It prevents invalid connection topologies by excluding elements that shouldn't be connection endpoints.
See [`custom_components/haeo/elements/__init__.py`](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/elements/__init__.py) for the connectivity level assigned to each element type.

### Element-specific implementations

Each element type has its own flow class in `custom_components/haeo/flows/elements/<element>.py`:

- `BatterySubentryFlowHandler` - Battery element configuration
- `BatterySectionSubentryFlowHandler` - Battery Section configuration
- `ConnectionSubentryFlowHandler` - Connection configuration
- `GridSubentryFlowHandler` - Grid configuration
- `InverterSubentryFlowHandler` - Inverter configuration
- `LoadSubentryFlowHandler` - Load configuration
- `NodeSubentryFlowHandler` - Network node configuration
- `SolarSubentryFlowHandler` - Solar system configuration

Each flow defines element-specific schema fields, defaults, and validation logic.

## ChooseSelector Config Flow Pattern

Element types use a sectioned configuration flow with Home Assistant's `ChooseSelector`.
This selector provides a dropdown letting users pick between different input methods for each field.

### Input Options

Each configurable field uses a `ChooseSelector` with these options:

| Choice   | Description                              | Storage Format            |
| -------- | ---------------------------------------- | ------------------------- |
| Entity   | Value comes from Home Assistant sensors  | Entity ID string or list  |
| Constant | User enters a fixed value directly       | Numeric value or boolean  |
| None     | Field is not used (optional fields only) | Field omitted from config |

Required fields offer "Entity" and "Constant" choices.
Optional fields also include "None" to skip the constraint entirely.

### Sectioned Flow

Most elements configure all inputs in a single step:

1. User enters element name and connection target
2. For each input field, user selects "Entity", "Constant", or "None"
3. Based on selection, user either picks entities from a dropdown or enters a constant value inline
4. Submit creates the element with all configuration

Some elements add a follow-up step when optional settings are enabled.
For example, the battery flow presents a second step for undercharge and overcharge partitions when the user enables partitioning.

### UI Sections

Config flows group related fields using `data_entry_flow.section` so advanced settings can be collapsed by default.
Shared section definitions live in `custom_components/haeo/sections/` and include `common`, `pricing`, `efficiency`, `power_limits`, and `forecast`.
Element-specific sections live alongside the element flow and schema.
When using sections, translation strings for labels must live under
`step.<step_id>.sections.<section_key>.data.<field_name>` (and `data_description` if needed).

### Implementation Pattern

The ChooseSelector utilities are in `custom_components/haeo/flows/field_schema.py`:

- `build_choose_schema_entry()`: Creates the ChooseSelector with entity/constant/none options
- `build_choose_selector()`: Builds the selector with proper choice ordering
- `get_preferred_choice()`: Determines which choice should be pre-selected based on defaults or current config
- `get_choose_default()`: Provides default values for the nested selector
- `convert_choose_data_to_config()`: Converts ChooseSelector output to final config format
- `preprocess_sectioned_choose_input()`: Normalizes sectioned ChooseSelector input
- `validate_sectioned_choose_fields()`: Validates sectioned choose fields before conversion
- `convert_sectioned_choose_data_to_config()`: Converts sectioned ChooseSelector data into sectioned config

The choice ordering in `ChooseSelector` determines the pre-selected option.
The `get_preferred_choice()` function examines field defaults and current configuration to order choices appropriately.

### Entity Creation

HAEO creates input entities (number/switch) for fields configured with "Constant".
These entities allow runtime adjustment of constant values without reconfiguring the element.
Fields linked to external entities use those entities directly without creating HAEO input entities.

## Field Schema System

HAEO uses a typed schema system to define element configuration fields.
The schema system provides type safety, validation, and data loading from Home Assistant entities.

### ELEMENT_TYPES Registry

All element types are registered in `custom_components/haeo/elements/__init__.py`:

```python
ELEMENT_TYPES: dict[ElementType, ElementRegistryEntry] = {
    "battery": ElementRegistryEntry(
        schema=BatteryConfigSchema,  # TypedDict for UI configuration
        data=BatteryConfigData,  # TypedDict for loaded values
        defaults={...},  # Default field values
        translation_key="battery",  # For UI localization
        adapter=create_battery,  # Creates model elements
        extract=extract_battery,  # Extracts optimization results
    ),
    # ... other element types
}
```

The registry provides:

- **Schema/Data class pairs**: Dual TypedDict pattern for type safety
- **Default values**: Pre-populated fields in the UI
- **Adapter functions**: Convert loaded data to model elements
- **Result extractors**: Convert optimization results to sensor data

### Schema vs Data Mode

Each element type has two TypedDict definitions:

**Schema mode** (`*ConfigSchema`): What the user enters in the UI

- Contains entity IDs as strings
- Used during config flow form display and validation

**Data mode** (`*ConfigData`): What the optimizer uses

- Contains loaded numeric values
- Produced by the `load()` function during coordinator updates

```python
# Schema mode: entity IDs with Annotated metadata
class BatteryConfigSchema(TypedDict):
    capacity: EnergySensorFieldSchema  # Annotated[str, EntitySelect(...), TimeSeries(...)]


# Data mode: loaded values
class BatteryConfigData(TypedDict):
    capacity: EnergySensorFieldData  # Annotated[list[float], ...]
```

### Field Metadata with Annotated

Fields use `Annotated` types with composable metadata markers:

```python
from typing import Annotated

# Define field type with composed metadata
EnergySensorFieldSchema = Annotated[
    str,
    EntitySelect(accepted_units=ENERGY_UNITS),
    TimeSeries(accepted_units=ENERGY_UNITS),
]


class BatteryConfigSchema(TypedDict):
    capacity: EnergySensorFieldSchema  # Entity ID with attached metadata
```

The composable metadata types are:

- **Validator subclasses**: Define schema validation and UI selectors (e.g., `PositiveKW`, `Percentage`, `EntitySelect`)
- **LoaderMeta subclasses**: Specify how values are loaded at runtime (e.g., `ConstantFloat`, `TimeSeries`)
- **Default**: Provides default values for config flow UI forms

### Available Field Types

Field types are defined in `custom_components/haeo/core/schema/fields.py`:

| Validator Class | Purpose                       | Base Type |
| --------------- | ----------------------------- | --------- |
| `PositiveKW`    | Positive power values in kW   | `float`   |
| `AnyKW`         | Power flow (pos or neg) in kW | `float`   |
| `PositiveKWH`   | Positive energy values in kWh | `float`   |
| `Price`         | Price values in \$/kWh        | `float`   |
| `Percentage`    | Percentage values (0-100)     | `float`   |
| `BatterySOC`    | Battery SOC percentage        | `float`   |
| `Boolean`       | Boolean flags                 | `bool`    |
| `Name`          | Free-form text names          | `str`     |
| `ElementName`   | References to other elements  | `str`     |
| `EntitySelect`  | Entity sensor references      | `str`     |

### Data Loading Flow

The schema system integrates with data loading:

1. User enters entity IDs in config flow (Schema mode)
2. Voluptuous validators ensure valid entity selection
3. On coordinator update, `load()` converts Schema → Data mode
4. LoaderMeta markers determine which loader extracts values from Home Assistant
5. Adapter functions receive Data mode config to create model elements

For details on loaders, see [Data Loading](data-loading.md).

## Options Flow

The options flow allows users to edit hub optimization settings after initial setup.
Elements are managed as separate config entries (added/edited/removed through the main integration flow), not through the options flow.

The options flow implementation is in `custom_components/haeo/flows/options.py`.

### Key points

- Options flow edits hub-level optimization settings (planning horizon preset, tier configuration, debounce window, advanced mode, forecast recording)
- Element configuration happens via separate config entries
- Settings stored in `config_entry.data` under section keys
- Changes trigger coordinator reload to apply new parameters

## Element Management

Elements are not managed through the hub's options flow.
Instead, users add/edit/remove elements as independent config entries through the main "Add Integration" flow.

### User workflow

**Adding elements:**

1. Navigate to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "HAEO"
4. Select element type (battery, grid, etc.)
5. Choose parent hub
6. Configure element parameters

**Editing elements:**

1. Find the element entry in **Devices & Services**
2. Click **Configure** on the element entry
3. Modify parameters
4. Submit changes

**Removing elements:**

1. Find the element entry in **Devices & Services**
2. Click the three-dot menu
3. Select **Delete**

The hub coordinator automatically detects element changes on the next update cycle.
See [user configuration guide](../user-guide/configuration.md) for end-user instructions.

## Testing Config Flow

Config flow testing uses Home Assistant's [testing fixtures](https://developers.home-assistant.io/docs/development_testing/#test-fixtures) and follows standard patterns.

Comprehensive test coverage is in `flows/tests/`, including:

- Hub flow success and duplicate prevention
- Element flow with hub selection
- Options flow for editing settings
- Error handling scenarios
- Validation logic

Example test pattern:

```python
async def test_hub_flow_success(hass: HomeAssistant) -> None:
    """Test successful hub creation."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_NAME: "Test Hub", CONF_HORIZON_HOURS: 48},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {INTEGRATION_TYPE: INTEGRATION_TYPE_HUB}
```

## Related Documentation

<div class="grid cards" markdown>

- :material-sitemap:{ .lg .middle } **Architecture**

    ---

    Overall system design.

    [:material-arrow-right: Architecture guide](architecture.md)

- :material-database:{ .lg .middle } **Data Loading**

    ---

    Field types and data validation.

    [:material-arrow-right: Data loading guide](data-loading.md)

- :material-network:{ .lg .middle } **Energy Models**

    ---

    Element type implementations.

    [:material-arrow-right: Energy models](energy-models.md)

- :material-test-tube:{ .lg .middle } **Testing**

    ---

    Testing patterns for config flows.

    [:material-arrow-right: Testing guide](testing.md)

- :material-file-document:{ .lg .middle } **User Configuration Guide**

    ---

    End-user configuration instructions.

    [:material-arrow-right: Configuration guide](../user-guide/configuration.md)

- :material-home-assistant:{ .lg .middle } **Home Assistant Config Flow**

    ---

    Upstream pattern documentation.

    [:material-arrow-right: HA Config Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)

- :material-home-assistant:{ .lg .middle } **Data Entry Flow**

    ---

    Flow framework reference.

    [:material-arrow-right: Data Entry Flow](https://developers.home-assistant.io/docs/data_entry_flow_index/)

</div>
