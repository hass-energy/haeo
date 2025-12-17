# Configuration Flow Development

Guide to HAEO's ConfigSubentry-based configuration flow implementation.

## Overview

HAEO uses Home Assistant's **ConfigSubentry architecture** where each element is managed as a subentry:

1. **Hub flow** (in `custom_components/haeo/flows/hub.py`): Creates main hub entry with optimization settings
2. **Element flows** (in `custom_components/haeo/flows/element.py`): Creates element ConfigSubentries using `ConfigSubentryFlow`
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

Hub entries are identified by the presence of `integration_type: "hub"` in their data:

```python
{
    "entry_id": "abc123...",
    "domain": "haeo",
    "title": "Home Energy System",
    "data": {
        "integration_type": "hub"  # Marker to identify hub entries
    },
    "options": {
        "horizon_hours": 48,
        "period_minutes": 5,
    },
}
```

Optimization settings are stored in `options` (user-editable), while the hub marker is stored in `data` (immutable).
The hub flow implementation is in `custom_components/haeo/flows/hub.py`.

### Key implementation points

- Hub flow uses standard config flow pattern with user step
- Prevents duplicate hub names by checking existing entries
- Stores optimization settings in `options` for later editing via options flow
- Hub marker in `data` allows coordinator to identify hub entries

## Element Flows

Element subentries are created through separate config flows, one per element type.
All element flows inherit from a common base class that handles parent hub selection and entry creation.

### Element entry structure

Element entries link to their parent hub via `parent_entry_id`:

```python
{
    "entry_id": "def456...",
    "domain": "haeo",
    "title": "Home Battery",
    "data": {
        "element_type": "battery",
        "parent_entry_id": "abc123...",  # Links to hub entry
        "capacity": 13500,
        "charge_power": 5000,
        # ... element-specific configuration
    },
}
```

### Base element flow pattern

All element flows extend `ElementConfigFlow` which provides:

- Parent hub selection (auto-selects if only one hub exists)
- Entry creation with proper parent linkage
- Duplicate prevention
- Standard error handling

The element flow base class is in `custom_components/haeo/flows/element.py`.

### Element-specific implementations

Each element type has its own flow class in `custom_components/haeo/flows/`:

- `BatteryConfigFlow` - Battery element configuration
- `GridConfigFlow` - Grid connection configuration
- `PhotovoltaicsConfigFlow` - PV system configuration
- `ConstantLoadConfigFlow` - Constant load configuration
- `ForecastLoadConfigFlow` - Forecast-based load configuration
- `NodeConfigFlow` - Network node configuration

Each flow defines element-specific schema fields, defaults, and validation logic.

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
    capacity: EnergySensorFieldSchema  # Annotated[str | list[str], SensorFieldMeta(...)]


# Data mode: loaded values
class BatteryConfigData(TypedDict):
    capacity: EnergySensorFieldData  # Annotated[TimeSeries | float, ...]
```

### Field Metadata with Annotated

Fields use `Annotated` types to attach metadata without changing the base type:

```python
from typing import Annotated

# Define field type with metadata
EnergySensorFieldSchema = Annotated[str | list[str], SensorFieldMeta(accepted_units=[UnitSpec(...)], multiple=True)]


class BatteryConfigSchema(TypedDict):
    capacity: EnergySensorFieldSchema  # Entity ID with attached metadata
```

The `FieldMeta` subclasses provide:

- **`field_type`**: "constant" or "sensor" for loader selection
- **`loader`**: Instance that loads data from entities
- **`create_schema()`**: Returns Voluptuous validators for the config flow

### Available Field Types

Field types are defined in `custom_components/haeo/schema/fields.py`:

| Field Meta Class       | Purpose                      | Base Type          |
| ---------------------- | ---------------------------- | ------------------ |
| `PowerFieldMeta`       | Constant power values        | `float`            |
| `EnergyFieldMeta`      | Constant energy values       | `float`            |
| `PriceFieldMeta`       | Constant price values        | `float`            |
| `PercentageFieldMeta`  | Percentage values (0-100)    | `float`            |
| `BooleanFieldMeta`     | Boolean flags                | `bool`             |
| `NameFieldMeta`        | Free-form text names         | `str`              |
| `ElementNameFieldMeta` | References to other elements | `str`              |
| `SensorFieldMeta`      | Entity sensor references     | `str \| list[str]` |

### Data Loading Flow

The schema system integrates with data loading:

1. User enters entity IDs in config flow (Schema mode)
2. Voluptuous validators ensure valid entity selection
3. On coordinator update, `load()` converts Schema → Data mode
4. Each field's loader extracts values from Home Assistant entities
5. Adapter functions receive Data mode config to create model elements

For details on loaders, see [Data Loading](data-loading.md).

## Options Flow

The options flow allows users to edit hub optimization settings after initial setup.
Elements are managed as separate config entries (added/edited/removed through the main integration flow), not through the options flow.

The options flow implementation is in `custom_components/haeo/flows/hub.py`.

### Key points

- Options flow only edits hub-level optimization settings (horizon, period, solver)
- Element configuration happens via separate config entries
- Settings stored in `config_entry.options` (not `data`)
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

Comprehensive test coverage is in `tests/test_config_flow.py`, including:

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
