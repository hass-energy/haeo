# Testing

HAEO uses pytest with 95% minimum coverage target.

## Test Organization

- `tests/conftest.py` - Shared fixtures (Home Assistant instance, mock config entries, common scenarios)
- `tests/test_*.py` - Component tests (model, coordinator, sensors, flows)
- `tests/scenarios/*.py` - Complete system integration tests

## Test Structure

**Unit tests**: Fast, isolated verification of element constraints, cost functions, data validation

**Integration tests**: Coordinator data flow, sensor updates, config entry lifecycle

**Scenario tests**: Complete battery + solar + grid systems with realistic data

## Adding Element Tests

When adding new element types:

1. Add to `ELEMENT_TYPES` in `const.py`
2. Add test data in `tests/flows/test_data/`
3. Parameterized tests automatically include the new type

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
