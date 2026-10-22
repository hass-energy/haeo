---
name: testing
description: Test standards for HAEO — where tests live (colocated tests/ directories), coverage decision tree, bug-fix TDD, function-style and parametrized tests, registry-driven element test data, shared fixtures in conftest.py, the runtime translation checker, scenario and guide tests, and config flow testing. Use when writing, fixing, or reorganizing tests, or when deciding how to cover new code.
---

# Testing standards

## Where tests live

Tests are colocated with the code they test, in a `tests/` directory inside each package, such as `core/model/tests/` or `flows/elements/tests/`.
The top-level `tests/` directory holds only scenario tests in `tests/scenarios/`, guide tests in `tests/guides/`, and tests of the CLI tools.

Every test runs under `timeout = 5` and `filterwarnings = ["error"]`, so a new warning fails it and a hang surfaces as a timeout.

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

### Judging an existing test

The decision tree above asks what a *new* test should be.
When reviewing tests that already exist, decide keep, combine, or remove against these:

- **Behavior**: what real contract does it validate? A test that cannot answer this is a remove candidate.
- **Assertions**: are they meaningful? Missing or trivial assertions mean remove or fix.
- **Redundancy**: does another test already cover the behavior? Prefer combining into a parametrized case.
- **Edge cases**: are the boundaries covered, or only the happy path?
- **Type overlap**: tests that re-prove what pyright already guarantees are redundant by construction.
- **Over-mocking**: a test that only proves its mocks were called tests nothing.
- **Flakiness risk**: dependence on wall-clock time, randomness, ordering, or external services.
- **Cost versus value**: long or brittle tests that add little behavioral coverage.

Removing a test is a real improvement when it fails these, but coverage on changed lines must not drop.
Verify with `uv run pytest --cov=custom_components/haeo --cov-branch --cov-report=term-missing` before and after.

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

- Each element module defines a `VALID_CASES` list
- Cases are aggregated in `__init__.py` for parametrized tests
- A case's `factory` builds the element and its `inputs` fix or bound the element's power
- Cases specify `expected_outputs`

If lines cannot be covered by exercising input data, it implies those lines are unreachable.
Add test cases to the data modules rather than creating element-specific test files.

## Element test data

Suites that cover every element type iterate the adapter registry `ELEMENT_TYPES` and import one data module per type, so a new type fails them until its data exists:

- `core/adapters/elements/tests/test_data/{type}.py` defines `CREATE_CASES` and `OUTPUTS_CASES`, which `test_mapping.py` runs through each adapter's `model_elements()` and `outputs()`.
- `flows/tests/test_data/{type}.py` defines `VALID_DATA` and `INVALID_DATA`.
    Each `VALID_DATA` config is in the shape the subentry stores, so the flow tests submit it and the schema tests in `elements/tests/` validate it as a stored config.

Add a case to these modules rather than writing a per-type test.

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

## Fixtures

Shared fixtures and helpers live in the root `conftest.py`, such as `hub_entry` for a hub config entry, `add_participant()` for an element subentry to connect to, and `added_entities()` for the entities a platform added.
Reuse them before writing a new fixture.

## Translations in tests

The pytest plugin `custom_components/haeo/translations/tests/runtime_checks.py` runs in every test.
It fails a test that shows a flow form, abort, repair issue, translated error, entity name, or enum state whose string or placeholder `en.json` lacks.
Use real translation keys in tests, never invented ones; see the `translations` skill.

## Scenario and guide tests

Scenario tests in `tests/scenarios/` run whole optimizations and compare them with snapshots.
Select them with `-m scenario`; `uv run check` runs them as their own gate and CI runs them in its scenario job.
The `scenarios` skill covers them.

Guide tests in `tests/guides/` render the user guide screenshots in Playwright Firefox and are selected with `-m guide`.
They run in the `guides.yml` workflow, not in `uv run check`.
Run them in parallel with `uv run pytest -m guide -n 8`.

## Config flow testing

Test both success paths and error handling, asserting the real error keys the flow sets:

```python
async def test_user_flow_success(hass):
    """Test successful user flow."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={...})
    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_user_flow_duplicate_name(hass):
    """Test that a name already in use is rejected."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={...})
    assert result["errors"] == {"name": "name_exists"}
```
