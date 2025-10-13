# Testing

HAEO uses pytest for testing.

## Running Tests

```bash
# All tests
uv run pytest

# Specific file
uv run pytest tests/test_model.py

# With coverage
uv run pytest --cov=custom_components.haeo --cov-report=html

# Verbose
uv run pytest -v --tb=short
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_model.py            # Entity/network tests
├── test_coordinator.py      # Coordinator tests
├── test_sensor.py           # Sensor tests
├── flows/
│   ├── test_config_flow.py
│   └── test_options_flow.py
└── scenarios/
    └── test_systems.py
```

## Example Tests

### Model Test

```python
def test_battery_creation():
    battery = Battery(
        name="test",
        period=1.0,
        n_periods=24,
        capacity=10.0,
        max_charge_power=5.0,
        max_discharge_power=5.0,
    )

    assert battery.capacity == 10.0
    assert len(battery.power_consumption) == 24
    assert len(battery.energy) == 24
```

### Network Test

```python
def test_simple_optimization():
    network = Network(name="test", period=1.0, n_periods=24)

    # Add entities
    network.elements["grid"] = Grid(...)
    network.elements["load"] = ConstantLoad(...)
    network.elements["net"] = Net(...)

    # Add connections
    network.connections.append(Connection(...))

    # Optimize
    cost = network.optimize()
    assert cost > 0
```

### Integration Test

```python
async def test_setup_entry(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    assert await async_setup_entry(hass, mock_config_entry)
    await hass.async_block_till_done()
```

## Coverage Target

**Minimum**: 95% for all modules

Check coverage:

```bash
uv run pytest --cov=custom_components.haeo --cov-report=term-missing
```

## Key Testing Areas

- Entity creation and constraints
- Network building and validation
- Optimization solve
- Coordinator update cycle
- Config flow steps
- Sensor updates

## Related Documentation

- [Architecture](architecture.md)
- [Energy Models](energy-models.md)
