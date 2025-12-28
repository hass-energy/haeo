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
- `tests/test_data/elements/` for test data matching element structure

## Element subfolder structure

Each element type lives in its own subfolder under `elements/`:

```
elements/battery/
├── __init__.py      # Public exports
├── schema.py        # ConfigSchema and ConfigData TypedDicts
├── flow.py          # Config flow implementation
└── adapter.py       # load(), available(), create_model_elements(), outputs()
```

## Schema module (`schema.py`)

Defines explicit TypedDicts without annotation-based metadata:

```python
class BatteryConfigSchema(TypedDict):
    """Schema mode: entity IDs for UI configuration."""

    element_type: Literal["battery"]
    name: str
    capacity: str  # Entity ID


class BatteryConfigData(TypedDict):
    """Data mode: loaded values for optimization."""

    element_type: Literal["battery"]
    name: str
    capacity: list[float]  # Loaded kWh values
```

## Flow module (`flow.py`)

Implements config flow with explicit voluptuous schemas:

```python
async def async_get_schema(hass: HomeAssistant, nodes: Sequence[str]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME): TextSelector(...),
            vol.Required(CONF_CAPACITY): EntitySelector(...),
        }
    )
```

## Adapter module (`adapter.py`)

Contains four key functions:

- **`available()`**: Check if config can be loaded (sensors exist)
- **`load()`**: Load sensor values into ConfigData
- **`create_model_elements()`**: Transform ConfigData into model params
- **`outputs()`**: Map model outputs to device sensors

## Registry

Elements register in `ELEMENT_TYPES` with:

```python
ElementRegistryEntry(
    flow_class=BatteryConfigFlow,
    available=battery.available,
    load=battery.load,
    create_model_elements=battery.create_model_elements,
    outputs=battery.outputs,
)
```

## Adding new element types

1. Create element subfolder with `__init__.py`, `schema.py`, `flow.py`, `adapter.py`
2. Define Schema and Data TypedDicts in `schema.py`
3. Implement config flow in `flow.py`
4. Implement `available()`, `load()`, `create_model_elements()`, `outputs()` in `adapter.py`
5. Register in `ELEMENT_TYPES` in `elements/__init__.py`
6. Add test data in `tests/test_data/elements/`
7. Add translations in `translations/en.json`
8. Document in `docs/user-guide/elements/` and `docs/modeling/device-layer/`
