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

## Scenario Testing

Scenario tests verify complete system integration with realistic Home Assistant data.
All scenarios are automatically discovered and tested by `tests/scenarios/test_scenarios.py`.

### Structure

Each scenario folder contains:

- `config.json` - HAEO configuration with elements and connections
- `states.json` - Filtered Home Assistant entity states

New scenarios are automatically discovered by the test runner (any `scenario*/` folder).

### Running Scenario Tests

```bash
# Run all scenarios (scenarios are skipped by default)
uv run pytest tests/scenarios/test_scenarios.py -m scenario

# Run specific scenario
uv run pytest tests/scenarios/test_scenarios.py::test_scenarios[scenario1] -m scenario

# Update snapshots after changes
uv run pytest tests/scenarios/test_scenarios.py -m scenario --snapshot-update
```

### Test Behavior

- Automatically extracts freeze time from most recent `last_updated` timestamp in states.json
- Parameterized test runs once per scenario with unique test ID
- Snapshots stored in `tests/scenarios/snapshots/test_scenarios.ambr`
- Visualizations generated in each scenario's `visualizations/` directory

For detailed scenario setup instructions, see `tests/scenarios/README.md`.

## Model Element Testing

Model element tests are organized in `tests/model/` with structured test data:

- `test_elements.py` - Parametrized tests for element outputs and validation
- `test_data/__init__.py` - Utilities and test case aggregation
- `test_data/element.py` - Base Element test cases
- `test_data/battery.py` - Battery-specific test cases
- `test_data/connection.py` - Connection test cases
- `test_data/grid.py` - Grid test cases
- `test_data/solar.py` - Solar test cases

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
            "battery_power_charge": {
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

When adding a new element type, create a parallel test directory:

```
tests/elements/{element_type}/
├── __init__.py
├── test_adapter.py   # Tests for available() and load() functions
└── test_flow.py      # Config flow tests for user and reconfigure steps
```

**For adapter tests** (`test_adapter.py`):

1. Test `available()` returns `True` when all required sensors exist
2. Test `available()` returns `False` when required sensors are missing
3. Test `load()` correctly transforms `ConfigSchema` to `ConfigData`
4. Test `load()` handles optional fields appropriately

**For flow tests** (`test_flow.py`):

1. Test user step creates entry with valid input
2. Test user step shows form initially (no input)
3. Test validation errors (empty name, duplicate name)
4. Test reconfigure step preserves current values
5. Test reconfigure with participant that no longer exists
6. Test element-specific validation (e.g., source != target for connections)

Also add test data in `tests/flows/test_data/{element_type}.py` for parametrized flow tests.

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
- Pyright type checking

## Related Documentation

<div class="grid cards" markdown>

- :material-sitemap:{ .lg .middle } **Architecture**

    ---

    System design overview.

    [:material-arrow-right: Architecture guide](architecture.md)

- :material-network:{ .lg .middle } **Energy Models**

    ---

    Model implementation details.

    [:material-arrow-right: Energy models](energy-models.md)

- :material-sync:{ .lg .middle } **Coordinator**

    ---

    Update cycle patterns.

    [:material-arrow-right: Coordinator guide](coordinator.md)

- :material-database:{ .lg .middle } **Data Loading**

    ---

    Loader testing approaches.

    [:material-arrow-right: Data loading guide](data-loading.md)

- :material-cog:{ .lg .middle } **Config Flow**

    ---

    Flow testing patterns.

    [:material-arrow-right: Config flow guide](config-flow.md)

- :material-hammer-wrench:{ .lg .middle } **Setup**

    ---

    Environment setup for development.

    [:material-arrow-right: Setup guide](setup.md)

</div>
