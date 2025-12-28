---
applyTo: custom_components/haeo/elements/**
description: Elements layer development standards
globs: [custom_components/haeo/elements/**]
alwaysApply: false
---

# Elements layer development

The elements layer bridges Home Assistant configuration with the LP model layer.
Each element type has its own subfolder with dedicated modules for schema, flow, and adapter logic.

When modifying elements, ensure corresponding updates to:

- `docs/user-guide/elements/` for user-facing configuration
- `docs/modeling/device-layer/` for mathematical formulation
- `tests/elements/{element_type}/` for element tests

## Element subfolder structure

Each element type lives in its own subfolder under `elements/`:

```
elements/battery/
├── __init__.py      # Public exports
├── schema.py        # ConfigSchema, ConfigData TypedDicts, DEFAULTS dict
├── flow.py          # Config flow implementation
└── adapter.py       # available(), load(), create_model_elements(), outputs()
```

## Schema module (`schema.py`)

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
    efficiency: float  # Default applied during load
```

**Important**: Do not put numeric values in comments (e.g., "Default 99%").
The DEFAULTS dict is the single source of truth for default values.

## Flow module (`flow.py`)

Implements config flow using DEFAULTS for suggested values:

```python
from .schema import CONF_NAME, CONF_EFFICIENCY, DEFAULTS

def _build_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_NAME): TextSelector(...),
        vol.Optional(CONF_EFFICIENCY): NumberSelector(...),  # No default here
    })

# In flow handler:
schema = _build_schema()
schema = self.add_suggested_values_to_schema(schema, DEFAULTS)  # Apply defaults
```

## Adapter module (`adapter.py`)

Contains four key functions:

- **`available()`**: Check if config can be loaded (sensors exist)
- **`load()`**: Load sensor values into ConfigData, applying DEFAULTS
- **`create_model_elements()`**: Transform ConfigData into model params
- **`outputs()`**: Map model outputs to device sensors

## Registry

Elements register in `ELEMENT_TYPES` as `ElementAdapter` instances:

```python
from custom_components.haeo.elements import ElementAdapter, ConnectivityLevel

ELEMENT_TYPES: dict[ElementType, ElementAdapter] = {
    battery.ELEMENT_TYPE: ElementAdapter(
        element_type=battery.ELEMENT_TYPE,
        flow_class=battery.BatterySubentryFlowHandler,
        available=battery.available,
        load=battery.load,
        create_model_elements=battery.create_model_elements,
        outputs=battery.outputs,
        connectivity=ConnectivityLevel.ADVANCED,
    ),
}
```

## Adding new element types

1. Create element subfolder with `__init__.py`, `schema.py`, `flow.py`, `adapter.py`
2. Define Schema and Data TypedDicts in `schema.py` with DEFAULTS dict for optional fields
3. Implement config flow in `flow.py` using DEFAULTS for suggested values
4. Implement `available()`, `load()`, `create_model_elements()`, `outputs()` in `adapter.py`
5. Register `ElementAdapter` instance in `ELEMENT_TYPES` in `elements/__init__.py`
6. Add flow test data in `tests/flows/test_data/{element_type}.py`
7. Add element tests in `tests/elements/{element_type}/` with `test_adapter.py`, `test_flow.py`, `test_model.py`
8. Add translations in `translations/en.json`
9. Document in `docs/user-guide/elements/` and `docs/modeling/device-layer/`
