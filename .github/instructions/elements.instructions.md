---
applyTo: custom_components/haeo/elements/**
description: Elements layer development standards
globs: [custom_components/haeo/elements/**]
alwaysApply: false
---

# Elements layer development

The elements layer bridges Home Assistant configuration with the LP model layer.
Each element type is split across three packages: schema, adapter, and flow.

When modifying elements, ensure corresponding updates to:

- `docs/user-guide/elements/` for user-facing configuration
- `docs/modeling/device-layer/` for mathematical formulation
- Colocated `tests/` directories for element tests

## Element file locations

Each element type has files in three separate packages:

```
core/schema/elements/{type}.py     # ConfigSchema, ConfigData TypedDicts, DEFAULTS dict
core/adapters/elements/{type}.py   # available(), inputs(), model_elements(), outputs()
flows/elements/{type}.py           # Config flow implementation
```

The `elements/` package itself contains the registry and shared infrastructure:

```
elements/
├── __init__.py          # ELEMENT_TYPES registry, ElementAdapter, type utilities
├── availability.py      # Sensor availability checking
├── field_hints.py       # Field hint generation
├── field_schema.py      # Field schema utilities
└── input_fields.py      # Input field definitions
```

## Schema module (`core/schema/elements/{type}.py`)

Defines explicit TypedDicts and a DEFAULTS dict for optional fields:

```python
ELEMENT_TYPE: Final = "battery"

# Configuration field names
CONF_CAPACITY: Final = "capacity"
CONF_EFFICIENCY: Final = "efficiency"

# Default values for optional fields
DEFAULTS: Final[dict[str, float]] = {
    CONF_EFFICIENCY: 99.0,
}


class BatteryConfigSchema(TypedDict):
    """Schema mode: entity IDs for UI configuration."""

    element_type: Literal["battery"]
    name: str
    capacity: list[str]  # Entity IDs
    efficiency: NotRequired[float]  # Optional with default in DEFAULTS


class BatteryConfigData(TypedDict):
    """Data mode: loaded values for optimization."""

    element_type: Literal["battery"]
    name: str
    capacity: list[float]  # Loaded kWh values
    efficiency: NotRequired[float]  # Default applied during model_elements
```

**Important**: Do not put numeric values in comments (e.g., "Default 99%").
The DEFAULTS dict is the single source of truth for default values.

## Flow module (`flows/elements/{type}.py`)

Implements config flow using DEFAULTS for suggested values:

```python
from custom_components.haeo.core.schema.elements.battery import CONF_NAME, CONF_EFFICIENCY, DEFAULTS


def _build_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME): TextSelector(...),
            vol.Optional(CONF_EFFICIENCY): NumberSelector(...),  # No default here
        }
    )


# In flow handler:
schema = _build_schema()
schema = self.add_suggested_values_to_schema(schema, DEFAULTS)  # Apply defaults
```

## Adapter module (`core/adapters/elements/{type}.py`)

Contains key functions:

- **`available()`**: Check if config can be loaded (sensors exist)
- **`inputs()`**: Define input fields for entity creation and loading
- **`model_elements()`**: Transform ConfigData into model params
- **`outputs()`**: Map model outputs to device sensors

## Registry

Elements register in `ELEMENT_TYPES` as adapter instances:

```python
from custom_components.haeo.elements import ElementAdapter, ConnectivityLevel

ELEMENT_TYPES: dict[ElementType, ElementAdapter] = {
    battery.ELEMENT_TYPE: battery.adapter,
}
```

## Adding new element types

1. Define Schema and Data TypedDicts in `core/schema/elements/{type}.py` with DEFAULTS dict for optional fields
2. Implement config flow in `flows/elements/{type}.py` using DEFAULTS for suggested values
3. Implement `available()`, `inputs()`, `model_elements()`, `outputs()` in `core/adapters/elements/{type}.py`
4. Register `ElementAdapter` instance in `ELEMENT_TYPES` in `elements/__init__.py`
5. Add flow test data in `flows/tests/test_data/{type}.py`
6. Add adapter tests in `core/adapters/elements/tests/`
7. Add flow tests in `flows/elements/tests/`
8. Add translations in `translations/en.json`
9. Document in `docs/user-guide/elements/` and `docs/modeling/device-layer/`
