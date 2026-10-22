# Typing Philosophy

HAEO uses Python's type system to prevent errors at development time rather than catching them at runtime.
This document describes the project's typing conventions and philosophy.

## Core principles

### Type at boundaries

Type objects as early as possible at system boundaries.
External data (API responses, sensor values, user input) should be validated and typed immediately upon entry.

```python
# ✅ Good: Type at the boundary
def load_config(raw_data: dict[str, object]) -> BatteryConfigData:
    """Validate and type external data immediately."""
    return BatteryConfigData(
        name=raw_data["name"],
        capacity=float(raw_data["capacity"]),
        # ... validation happens here
    )


# ❌ Bad: Pass untyped data through the system
def process_config(raw_data: dict[str, object]) -> None:
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

### Schema vs data mode

HAEO uses a dual TypedDict pattern for element configuration:

- **Schema mode**: Contains schema values (what the config flow stores in the subentry)
- **Data mode**: Contains loaded values (what the adapters and optimizer use at runtime)

Each element defines these types in its own schema module:

```python
# core/schema/elements/battery.py


class StorageSocConfig(TypedDict):
    """Schema mode: an entity, constant, or none value per field."""

    capacity: EntityValue | ConstantValue


class StorageSocData(TypedDict):
    """Data mode: loaded values for optimization."""

    capacity: NDArray[np.float64]  # kWh at each horizon boundary
```

The config loader (`core/data/loader/config_loader.py`) converts Schema mode to Data mode at the boundary, as each field's hint directs.
See [Config flow](config-flow.md#schema-vs-data-mode) for the full pattern.

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

- **`core/schema/elements/{type}.py`**: Defines the `ConfigSchema` and `ConfigData` TypedDicts and the field hints
- **`flows/elements/{type}.py`**: Implements the config flow, building its form from the field hints
- **`core/adapters/elements/{type}.py`**: Implements the adapter that turns `ConfigData` into model elements and outputs

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
- Do not import `typing.cast` (banned by Ruff); prefer `TypeGuard`, boundary typing, or `assert` for narrowing
- When the type checker cannot be satisfied otherwise, use `# type: ignore[...]` on the same line with a short comment explaining why a TypeGuard or other narrowing approach was not viable

## Avoiding Any

`typing.Any` disables type checking entirely for a value — every attribute access, call, and
assignment silently passes. Importing it is banned by Ruff (TID251), the same mechanism used for
`typing.cast`. Prefer, in order:

1. **A precise type**: a TypedDict, dataclass, Protocol, or union that describes the actual shape
2. **A generic `TypeVar`**: when the function relates its input and output types
3. **`object`**: for values that are genuinely unknown at a boundary. Unlike `Any`, `object`
    forces narrowing (isinstance, TypeGuard) before use — mistakes surface at the checker instead
    of at runtime

```python
# ✅ Good: object forces narrowing before use
def coerce_float(value: object) -> float | None:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None


# ❌ Bad: Any lets mistakes flow through silently
def coerce_float(value: Any) -> float | None:
    return value  # No checker error, wrong at runtime
```

For numpy arrays, use the concrete `NDArray[np.float64]` — every array in this codebase is
created as float64, so the generic `np.floating[Any]` form is never needed.

Some `Any` usage is structurally required and allowed with a justified `# noqa: TID251` on the
import line:

- dynamic test helpers that drive heterogeneous classes or monkeypatch methods (Mock-style)
- reflection over typing constructs (`get_origin`/`get_args` introspection)
- voluptuous schema dictionaries, which are heterogeneous by design
- Home Assistant framework signatures that are `Any`-typed upstream

Every remaining `# noqa: TID251` in the codebase carries a specific structural justification on
the import line. Adding a new one requires the same: a short comment stating why no precise type
can express the code. Remove the noqa when the last structural use in a file goes away.

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

## Next steps

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
