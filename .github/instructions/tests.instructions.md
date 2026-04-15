---
applyTo: tests/**
description: Testing standards
globs: [tests/**]
alwaysApply: false
---

# Testing standards

## Coverage requirements

Coverage is enforced by codecov which ensures coverage does not decrease from main on changed lines.
Focus on testing behavior and edge cases, not achieving arbitrary coverage percentages.

### Addressing uncovered lines

When encountering uncovered lines, work through this decision tree in order:

1. **Can this code be removed?** Dead code, unreachable branches, or defensive checks that upstream validation already prevents should be deleted rather than tested.
2. **Can stricter types eliminate this code?** If a branch exists only because a type is too wide, fix the types — even if the fix is far up the call chain. Removing code is better than testing unnecessary code.
3. **Can I add a parametrized case to an existing test?** If there is already a `@pytest.mark.parametrize` test covering similar behavior, add another case to it.
4. **Can I combine related tests into a new parametrized test?** Especially for stateless I/O-driven tests, grouping similar assertions into one parametrized test reduces duplication.
5. **Finally, write a bespoke test.** Only when none of the above apply, add a standalone test function that exercises a realistic behavioral scenario.

## Bug-fix TDD

When fixing a bug, follow red/green TDD:

1. **RED**: Write a failing test that reproduces the bug. Verify it fails for the expected reason.
2. **GREEN**: Make the minimal code change to pass the test.
3. **Verify**: Confirm all existing tests still pass.

## Test style

Use function-style pytest tests, not class-based test organization:

```python
# ✅ Good - function style
def test_battery_charges_correctly() -> None:
    battery = create_battery(capacity=10.0)
    result = battery.charge(5.0)
    assert result.soc == 0.5


# ❌ Bad - class style
class TestBattery:
    def test_charges_correctly(self) -> None: ...
```

## Parametrized data-driven tests

Use parametrized tests with test data modules rather than many similar test functions:

```python
@pytest.mark.parametrize("case", VALID_ELEMENT_CASES, ids=lambda c: c["description"])
def test_element_outputs(case: ElementTestCase) -> None:
    element = case["factory"](case["data"])
    outputs = element.outputs()
    assert outputs == case["expected_outputs"]
```

## Model test data structure

Model element tests use a data-driven pattern in `core/model/tests/test_data/`:

- Each element module defines `VALID_CASES` and `INVALID_CASES` lists
- Cases are aggregated in `__init__.py` for parametrized tests
- Factory functions create element instances with fixed LP variable values
- Test cases specify inputs and expected outputs

If lines cannot be covered by exercising input data, it implies those lines are unreachable.
Add test cases to the data modules rather than creating element-specific test files.

## Property access in tests

Access properties directly without None checks when you have created the entities:

```python
# ✅ Good - direct access
battery = network.elements["battery"]
assert battery.power == 1000

# ❌ Bad - unnecessary None checks
battery = network.elements.get("battery")
if battery is not None:
    assert battery.power == 1000
```

None checks reduce readability and make tests fragile to passing unexpectedly.

## Fixture patterns

```python
@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return mocked config entry."""
    return MockConfigEntry(
        title="Test Network",
        domain=DOMAIN,
        data={...},
        unique_id="test_unique_id",
    )


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> MockConfigEntry:
    """Set up integration for testing."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
```

## Snapshot testing

Use snapshots for complex data structures and entity states:

```python
@pytest.mark.usefixtures("init_integration")
async def test_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test sensor entities."""
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)
```

## Config flow testing

Test both success paths and error handling:

```python
async def test_user_flow_success(hass):
    """Test successful user flow."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={...})
    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_flow_connection_error(hass, mock_api_error):
    """Test connection error handling."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={...})
    assert result["errors"] == {"base": "cannot_connect"}
```
