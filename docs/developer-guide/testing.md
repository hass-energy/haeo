# Testing

HAEO uses pytest with 95% minimum coverage target.

For more information on testing Home Assistant integrations, see:

- [Testing integrations documentation](https://developers.home-assistant.io/docs/development_testing/)
- [pytest fixtures reference](https://developers.home-assistant.io/docs/development_testing/#test-fixtures)

## Test Organization

- `tests/conftest.py` - Shared fixtures (Home Assistant instance, mock config entries, common scenarios)
- `tests/model/` - Model element tests with structured test data
- `tests/flows/` - Config flow tests
- `tests/scenarios/` - Complete system integration tests

## Test Structure

**Unit tests**: Fast, isolated verification of element constraints, cost functions, data validation

**Integration tests**: Coordinator data flow, sensor updates, config entry lifecycle

**Scenario tests**: Complete battery + solar + grid systems with realistic data

## Model Element Testing

Model element tests are organized in `tests/model/` with structured test data:

- `test_elements.py` - Parametrized tests for element outputs and validation
- `test_data/__init__.py` - Utilities and test case aggregation
- `test_data/element.py` - Base Element test cases
- `test_data/battery.py` - Battery-specific test cases
- `test_data/connection.py` - Connection test cases
- `test_data/grid.py` - Grid test cases
- `test_data/photovoltaics.py` - Photovoltaics test cases

### Test Case Structure

Each test data module provides:

**Factory function**: Creates element instances with fixed LP variable values for testing

```python
def create(data: dict[str, Any]) -> Element:
    """Create a test Element instance with fixed values."""
    return Element(**data)
```

**VALID_CASES**: List of test cases with expected outputs

```python
VALID_CASES = [
    {
        "description": "Battery with full configuration",
        "factory": create,
        "data": {
            "name": "battery",
            "n_periods": 2,
            # etc
        },
        "expected_outputs": {
            "power_consumed": {
                "type": "power",
                "unit": "kW",
                "values": (1.0, 2.0),
                # etc
            },
        },
    }
]
```

**INVALID_CASES**: Test cases that should raise validation errors

```python
INVALID_CASES = [
    {
        "description": "Grid with import price length mismatch",
        "element_class": Grid,
        "data": {"name": "grid", "n_periods": 2, "price_import": (0.3,)},
        "expected_error": r"price_import length \(1\) must match n_periods \(2\)",
    }
]
```

### Adding New Element Tests

When adding a new element type:

1. Create `tests/model/test_data/new_element.py`
2. Implement `create(data)` factory function
3. Define `VALID_CASES` with expected outputs (type, unit, values)
4. Define `INVALID_CASES` for validation errors
5. Cases automatically included via aggregation in `__init__.py`

## Type Safety Philosophy

HAEO uses Python's type system to make certain error conditions impossible, rather than writing tests for defensive error logging.
This approach improves code quality and reduces test maintenance burden.

### When to Use Types Over Tests

**Use type safety (no tests needed) when:**

- Condition is guaranteed by architectural constraints (e.g., config entry IDs we control)
- Data structure is validated at creation boundaries (e.g., config flow validation)
- Error would represent a programming error, not a runtime condition

**Use defensive checks and tests when:**

- Handling external API responses (forecast parsers)
- Accessing Home Assistant state (entities might not exist)
- Processing user input (config flow initial entry)
- Dealing with optimization solver failures

### Type Safety Examples

**Config Entry Access:**

```python
# ❌ Old pattern with defensive logging
hub_entry = hass.config_entries.async_get_entry(hub_entry_id)
if not hub_entry:
    _LOGGER.warning("Hub entry %s not found", hub_entry_id)
    return {}

# ✅ New pattern with type assertion
from custom_components.haeo.elements import assert_config_entry_exists

hub_entry = assert_config_entry_exists(
    hass.config_entries.async_get_entry(hub_entry_id),
    hub_entry_id,
)
# No test needed - we control hub_entry_id, if missing it's a programming error
```

**Required Field Access:**

```python
# ❌ Old pattern with defensive logging
element_name = subentry.data.get("name")
if not element_name:
    _LOGGER.warning("Subentry %s has no name", subentry.subentry_id)
    continue

# ✅ New pattern with type assertion
from custom_components.haeo.elements import assert_subentry_has_name

element_name = assert_subentry_has_name(
    subentry.data.get("name_value"),
    subentry.subentry_id,
)
# No test needed - config flow guarantees name_value is set
```

**Element Type Validation:**

```python
# ❌ Old pattern with defensive logging
element_types = ELEMENT_TYPES.get(element_type)
if not element_types:
    _LOGGER.error("Unknown element type %s", element_type)
    continue

# ✅ New pattern with exhaustive checking
if element_type not in ELEMENT_TYPES:
    msg = f"Invalid element type {element_type} - config flow validation failed"
    raise RuntimeError(msg)
registry_entry = ELEMENT_TYPES[element_type]
schema_cls = registry_entry.schema
# No test needed - config flow validates element_type
```

### Benefits of Type Safety Over Tests

1. **Compile-time validation**: Catches errors before runtime
2. **Self-documenting**: Type signatures communicate invariants
3. **Reduced test maintenance**: No tests for "impossible" conditions
4. **Better error messages**: RuntimeError explains programming error vs silently logging
5. **Coverage focus**: Test coverage focuses on actual business logic

## Adding Config Flow Tests

When adding new element types:

1. Add to `ELEMENT_TYPES` in `elements/__init__.py`
2. Add config flow test data in `tests/flows/test_data/`
3. Parameterized tests automatically include the new type by iterating over `tuple(ELEMENT_TYPES)`

Parameterized tests marked with `@pytest.mark.parametrize` run once per element type.

## CI Requirements

All PRs must pass:

- All tests
- Coverage ≥ 95%
- Ruff linting
- MyPy type checking

## Related Documentation

- [Architecture](architecture.md) - System design
- [Energy Models](energy-models.md) - Model implementation
- [Coordinator](coordinator.md) - Update cycle
- [Data Loading](data-loading.md) - Loader testing
- [Config Flow](config-flow.md) - Flow testing patterns
- [Setup](setup.md) - Environment setup
