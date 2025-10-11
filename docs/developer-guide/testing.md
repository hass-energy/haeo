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
```

## Test Structure

```
tests/
├── test_init.py        # Integration setup
├── test_coordinator.py # Coordinator tests
├── test_model.py       # Model tests
├── test_sensor.py      # Sensor tests
├── flows/              # Config flow tests
└── scenarios/          # Integration scenarios
```

## Writing Tests

Use pytest fixtures:

```python
def test_battery_model():
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=24,
        capacity=10.0,
    )
    assert battery.capacity == 10.0
```

## Coverage Requirements

Target >95% test coverage for all modules.
