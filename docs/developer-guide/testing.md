# Testing

This guide covers testing strategies, patterns, and requirements for HAEO development.

## Overview

HAEO uses pytest with Home Assistant testing utilities for comprehensive test coverage.

**Testing goals**:

- **Unit tests**: Individual components in isolation
- **Integration tests**: Components working together
- **Scenario tests**: Complete system configurations
- **Coverage target**: >95% for all modules

## Running Tests

### Basic Test Execution

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_model.py

# Specific test function
uv run pytest tests/test_model.py::test_battery_creation

# With verbose output
uv run pytest -v

# With short traceback
uv run pytest --tb=short
```

### Coverage Reports

```bash
# Terminal coverage report
uv run pytest --cov=custom_components.haeo --cov-report=term

# HTML coverage report
uv run pytest --cov=custom_components.haeo --cov-report=html

# View HTML report (opens in browser)
open htmlcov/index.html
```

### Test Selection

```bash
# Run tests matching pattern
uv run pytest -k "battery"

# Run tests by marker
uv run pytest -m "slow"

# Skip marked tests
uv run pytest -m "not slow"
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_init.py             # Integration setup tests
├── test_coordinator.py      # Coordinator tests
├── test_model.py            # Model/entity tests
├── test_sensor.py           # Sensor tests
├── test_loaders.py          # Data loader tests
│
├── flows/                   # Config flow tests
│   ├── test_config_flow.py
│   └── test_options_flow.py
│
├── scenarios/               # Full integration scenarios
│   ├── test_simple_system.py
│   └── test_complex_system.py
│
├── data/                    # Test data
│   ├── fixtures/
│   └── sample_configs/
│
└── schema/                  # Schema validation tests
    └── test_validation.py
```

## Writing Unit Tests

### Model Tests

Test individual entity models:

```python
def test_battery_creation():
    """Test creating a battery entity."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=24,
        capacity=10.0,
        max_charge_power=5.0,
        max_discharge_power=5.0,
        efficiency=0.95,
    )

    assert battery.name == "test_battery"
    assert battery.capacity == 10.0
    assert len(battery.power_consumption) == 24
    assert len(battery.power_production) == 24
    assert len(battery.energy) == 24


def test_battery_constraints():
    """Test battery constraint generation."""
    battery = Battery(
        name="test",
        period=1.0,
        n_periods=24,
        capacity=10.0,
    )

    constraints = battery.constraints()

    # Should have energy balance constraints
    # n_periods - 1 energy balance equations
    assert len(constraints) == 23


def test_battery_cost():
    """Test battery cost calculation."""
    battery = Battery(
        name="test",
        period=1.0,
        n_periods=24,
        capacity=10.0,
        charge_cost=0.01,
        discharge_cost=0.01,
    )

    # Cost should be defined (may be zero if no charging)
    cost = battery.cost()
    assert cost is not None
```

### Network Tests

Test network building and optimization:

```python
def test_network_creation():
    """Test creating a network."""
    network = Network(
        name="test_network",
        period=1.0,
        n_periods=24,
    )

    assert network.name == "test_network"
    assert len(network.elements) == 0
    assert len(network.connections) == 0


def test_simple_optimization():
    """Test optimizing a simple network."""
    network = Network(name="test", period=1.0, n_periods=24)

    # Add grid (unlimited source)
    grid = Grid(
        name="grid",
        period=1.0,
        n_periods=24,
        import_price=0.25,
        export_price=0.10,
    )
    network.elements["grid"] = grid

    # Add load
    load = ConstantLoad(
        name="load",
        period=1.0,
        n_periods=24,
        power=3.0,
    )
    network.elements["load"] = load

    # Add net
    net = Net(name="main", period=1.0, n_periods=24)
    network.elements["main"] = net

    # Add connections
    network.connections.append(
        Connection(
            name="grid_to_net",
            period=1.0,
            n_periods=24,
            source="grid",
            target="main",
        )
    )
    network.connections.append(
        Connection(
            name="net_to_load",
            period=1.0,
            n_periods=24,
            source="main",
            target="load",
        )
    )

    # Should optimize successfully
    cost = network.optimize()
    assert cost > 0  # Should have import cost
    assert cost == pytest.approx(3.0 * 24 * 0.25, rel=0.01)
```

## Integration Tests

### Coordinator Tests

Test coordinator with Home Assistant:

```python
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import async_setup_entry
from custom_components.haeo.const import DOMAIN


@pytest.fixture
async def mock_config_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test HAEO",
        data={
            "horizon_hours": 24,
            "period_minutes": 5,
            "optimizer": "highs",
            "participants": {
                "grid": {"type": "grid", "name": "Grid"},
                "load": {"type": "constant_load", "name": "Load", "power": 3.0},
                "net": {"type": "net", "name": "Net"},
            },
            "connections": [
                {"source": "grid", "target": "net"},
                {"source": "net", "target": "load"},
            ],
        },
    )


async def test_setup_entry(hass: HomeAssistant, mock_config_entry):
    """Test setting up a config entry."""
    mock_config_entry.add_to_hass(hass)

    assert await async_setup_entry(hass, mock_config_entry)
    await hass.async_block_till_done()

    # Verify coordinator created
    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]
```

### Sensor Tests

Test sensor creation and updates:

```python
async def test_sensors_created(hass: HomeAssistant, initialized_entry):
    """Test that sensors are created."""
    # Wait for sensor setup
    await hass.async_block_till_done()

    # Check network sensors
    assert hass.states.get("sensor.test_network_optimization_cost")
    assert hass.states.get("sensor.test_network_optimization_status")

    # Check entity sensors
    assert hass.states.get("sensor.grid_power")
    assert hass.states.get("sensor.load_power")


async def test_sensor_updates(hass: HomeAssistant, initialized_entry):
    """Test that sensors update with coordinator."""
    # Trigger coordinator update
    coordinator = hass.data[DOMAIN][initialized_entry.entry_id]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # Check sensor states updated
    cost_sensor = hass.states.get("sensor.test_network_optimization_cost")
    assert cost_sensor.state not in ("unknown", "unavailable")

    # Check forecast attribute
    assert "forecast" in cost_sensor.attributes
```

## Scenario Tests

Test complete system configurations:

```python
def test_solar_battery_system(hass: HomeAssistant):
    """Test complete solar + battery + grid system."""
    config = {
        "participants": {
            "grid": {"type": "grid", ...},
            "solar": {"type": "photovoltaics", ...},
            "battery": {"type": "battery", ...},
            "load": {"type": "forecast_load", ...},
            "main": {"type": "net", ...},
        },
        "connections": [
            {"source": "grid", "target": "main"},
            {"source": "solar", "target": "main"},
            {"source": "battery", "target": "main"},
            {"source": "main", "target": "load"},
        ],
    }

    # Setup and run
    entry = MockConfigEntry(domain=DOMAIN, data=config)
    # ... test complete flow
```

## Test Fixtures

### Common Fixtures

Defined in `conftest.py`:

```python
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.haeo.const import DOMAIN


@pytest.fixture
def period():
    """Test period duration."""
    return 1.0  # 1 hour


@pytest.fixture
def n_periods():
    """Test number of periods."""
    return 24


@pytest.fixture
def simple_config():
    """Simple test configuration."""
    return {
        "horizon_hours": 24,
        "period_minutes": 60,
        "optimizer": "highs",
        "participants": {},
        "connections": [],
    }
```

### Entity Fixtures

```python
@pytest.fixture
def battery(period, n_periods):
    """Create test battery."""
    return Battery(
        name="test_battery",
        period=period,
        n_periods=n_periods,
        capacity=10.0,
        max_charge_power=5.0,
        max_discharge_power=5.0,
        efficiency=0.95,
    )


@pytest.fixture
def network(period, n_periods):
    """Create test network."""
    return Network(
        name="test",
        period=period,
        n_periods=n_periods,
    )
```

## Mocking

### Mocking Home Assistant Components

```python
from unittest.mock import patch, MagicMock

async def test_with_mock_sensor(hass):
    """Test with mocked sensor."""
    with patch("homeassistant.helpers.entity_platform.async_get_current_platform"):
        # Mock sensor reading
        hass.states.async_set("sensor.test", "5.0")

        # Test code that reads sensor
        value = hass.states.get("sensor.test").state
        assert value == "5.0"
```

### Mocking Data Loaders

```python
@pytest.fixture
def mock_loader():
    """Mock data loader."""
    loader = MagicMock()
    loader.get_forecast.return_value = [0.25] * 24
    loader.get_state.return_value = 50.0
    return loader
```

## Coverage Best Practices

### What to Test

**Always test**:

- Entity creation and initialization
- Constraint generation
- Cost calculation
- Network building and validation
- Coordinator update cycle
- Sensor creation and updates
- Config flow steps
- Error handling

**Edge cases**:

- Zero values
- Maximum values
- Missing data
- Invalid configurations
- Infeasible scenarios

### Coverage Report Analysis

```bash
# Generate HTML coverage report
uv run pytest --cov=custom_components.haeo --cov-report=html

# View report
open htmlcov/index.html
```

**Focus on**:

- Red (uncovered) lines
- Yellow (partial coverage) branches
- Complex functions with low coverage

### Improving Coverage

**Add tests for**:

- Error paths
- Edge cases
- Branch conditions
- Exception handling

**Example**:

```python
# Original: 80% coverage
def process_value(value):
    if value < 0:
        raise ValueError("Negative")
    return value * 2

# Test for 100% coverage
def test_process_value_positive():
    assert process_value(5) == 10

def test_process_value_negative():
    with pytest.raises(ValueError, match="Negative"):
        process_value(-1)
```

## Continuous Integration

Tests run automatically on GitHub Actions:

```.yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          pip install uv
          uv sync
          uv run pytest --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Related Documentation

- [Architecture](architecture.md) - System structure
- [Energy Models](energy-models.md) - What to test for entities
- [Coordinator](coordinator.md) - Coordinator testing strategies

## Next Steps

- Review existing tests in `tests/`
- Write tests for new features before implementation (TDD)
- Maintain >95% coverage for all new code
- Use scenario tests for complex configurations

[:octicons-arrow-right-24: Continue to Coordinator Guide](coordinator.md)
