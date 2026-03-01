# Typing Philosophy

HAEO uses Python's type system to prevent errors at development time rather than catching them at runtime.
This document describes the project's typing conventions and philosophy.

## Core Principles

### Type at boundaries

Type objects as early as possible at system boundaries.
External data (API responses, sensor values, user input) should be validated and typed immediately upon entry.

```python
# ✅ Good: Type at the boundary
def load_config(raw_data: dict[str, Any]) -> BatteryConfigData:
    """Validate and type external data immediately."""
    return BatteryConfigData(
        name=raw_data["name"],
        capacity=float(raw_data["capacity"]),
        # ... validation happens here
    )


# ❌ Bad: Pass untyped data through the system
def process_config(raw_data: dict[str, Any]) -> None:
    """Delay typing until deep in the call stack."""
    # raw_data flows through multiple functions untyped
    capacity = raw_data.get("capacity")  # Unknown type
```

### Prefer types over runtime checks

The type system should always be preferred over runtime checks where possible.
If a condition can be verified by the type checker, don't write a runtime check for it.

```python
# ✅ Good: Type system enforces constraint
def process_battery(battery: Battery) -> None:
    """Battery type guarantees required fields exist."""
    print(battery.capacity)  # Type checker knows this exists


# ❌ Bad: Runtime check for something types could handle
def process_battery(element: Element) -> None:
    """Check type at runtime when it could be typed."""
    if not isinstance(element, Battery):
        raise TypeError("Expected Battery")
    print(element.capacity)
```

### Tests verify behavior, not types

Tests should verify runtime behavior and business logic.
Tests should never check things that the type system can identify.

```python
# ✅ Good: Test verifies behavior
def test_battery_charges_correctly() -> None:
    battery = create_battery(capacity=10.0)
    result = battery.charge(5.0)
    assert result.soc == 0.5


# ❌ Bad: Test verifies type invariants
def test_battery_has_capacity() -> None:
    battery = create_battery(capacity=10.0)
    assert hasattr(battery, "capacity")  # Type checker already knows this
    assert isinstance(battery.capacity, float)  # Type annotation says this
```

## TypedDict for structured data

Use TypedDict to type dictionary-like structures, especially configuration data from Home Assistant.

### Schema vs Data mode

HAEO uses a dual TypedDict pattern for element configuration:

- **Schema mode**: Contains entity IDs as strings (what the user enters in config flow)
- **Data mode**: Contains loaded values (what the optimizer uses at runtime)

Each element defines these types in its own schema module:

```python
# core/schema/elements/battery.py


class BatteryConfigSchema(TypedDict):
    """Schema mode: entity IDs for UI configuration."""

    element_type: Literal["battery"]
    name: str
    capacity: str  # Entity ID string


class BatteryConfigData(TypedDict):
    """Data mode: loaded values for optimization."""

    element_type: Literal["battery"]
    name: str
    capacity: list[float]  # Loaded float values in kWh
```

The `load()` function in each element's adapter module converts from Schema mode to Data mode, performing validation and data loading at the boundary.

## Model element configs

Adapters output `ModelElementConfig` dictionaries for the model layer.
These configs are a discriminated union on `element_type`.
Use the model-layer element type constants from `custom_components/haeo/core/model/elements/__init__.py` to keep the discriminator consistent.

## TypeGuard for narrowing

Use TypeGuard to narrow types when the type checker cannot infer the narrowing automatically.

```python
from typing import TypeGuard


def is_battery_config(config: ElementConfigData) -> TypeGuard[BatteryConfigData]:
    """Narrow element config to battery-specific type."""
    return config["element_type"] == "battery"


def process_element(config: ElementConfigData) -> None:
    if is_battery_config(config):
        # Type checker knows config is BatteryConfigData here
        print(config["capacity"])  # Type-safe access
```

## Explicit element schemas

Each element type has dedicated modules split across three packages:

- **`core/schema/elements/{type}.py`**: Defines `ConfigSchema` and `ConfigData` TypedDicts with explicit types
- **`flows/elements/{type}.py`**: Implements config flow with voluptuous schemas and selectors
- **`core/adapters/elements/{type}.py`**: Contains `load()` function to convert Schema to Data mode

This explicit approach keeps the types clear at a glance:

```python
# core/schema/elements/solar.py
class SolarConfigSchema(TypedDict):
    element_type: Literal["solar"]
    name: str
    connection: str
    forecast: str  # Entity ID for forecast sensor


# flows/elements/solar.py
def async_get_schema(hass: HomeAssistant) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME): TextSelector(...),
            vol.Required(CONF_FORECAST): EntitySelector(...),
        }
    )
```

## Pyright configuration

HAEO uses Pyright in strict mode for type checking.
The configuration is in `pyproject.toml`:

```toml
[tool.pyright]
pythonVersion = "3.13"
typeCheckingMode = "strict"
```

### Common Pyright considerations

- All function parameters and return types must be annotated
- All class attributes must have type annotations
- Generic types must specify type parameters (`list[str]` not `list`)
- Use `cast()` sparingly and only when type checker cannot infer
- Prefer `assert` statements over `cast()` when narrowing types

## Assertion helpers

For cases where the type system cannot prove a condition but the code architecture guarantees it, use assertion helpers that provide clear error messages:

```python
def assert_config_entry_exists(
    entry: ConfigEntry | None,
    entry_id: str,
) -> ConfigEntry:
    """Assert that a config entry exists.

    Use when accessing entries by IDs that we control and know exist.
    """
    if entry is None:
        msg = f"Config entry {entry_id} not found - this indicates a programming error"
        raise RuntimeError(msg)
    return entry
```

These assertions:

- Replace defensive logging with clear failure modes
- Provide descriptive error messages for debugging
- Document the architectural invariant being relied upon
- Return the narrowed type for continued type-safe use

## Next Steps

<div class="grid cards" markdown>

- :material-sitemap:{ .lg .middle } **Architecture**

    ---

    Overall system design and component structure.

    [:material-arrow-right: Architecture guide](architecture.md)

- :material-cog:{ .lg .middle } **Config Flow**

    ---

    Schema system and field metadata patterns.

    [:material-arrow-right: Config flow guide](config-flow.md)

- :material-test-tube:{ .lg .middle } **Testing**

    ---

    Test patterns that respect type boundaries.

    [:material-arrow-right: Testing guide](testing.md)

</div>
