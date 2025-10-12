# Data Update Coordinator

This guide explains HAEO's coordinator implementation and update cycle.

## Overview

The coordinator is the central orchestrator that:

- Schedules optimization cycles
- Loads data from Home Assistant sensors
- Builds the optimization network
- Runs the LP solver
- Distributes results to sensors

**Pattern**: Extends Home Assistant's `DataUpdateCoordinator` for efficient polling and caching.

## Coordinator Class

```python
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

class HaeoDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for HAEO optimization updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize coordinator."""
        # Extract configuration
        self.horizon_hours = config_entry.data["horizon_hours"]
        self.period_minutes = config_entry.data["period_minutes"]
        self.optimizer = config_entry.data["optimizer"]

        # Calculate time parameters
        self.period = self.period_minutes / 60.0  # Convert to hours
        self.n_periods = int(self.horizon_hours / self.period)

        # Initialize data loaders
        self.sensor_loader = SensorLoader(hass)
        self.forecast_loader = ForecastLoader(hass)

        # Initialize coordinator
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=self.period_minutes),
            config_entry=config_entry,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data and run optimization."""
        # This is called every update_interval
        # See detailed implementation below
        pass
```

## Update Cycle

### Step 1: Load Current Data

```python
async def _async_update_data(self) -> dict[str, Any]:
    """Main update method."""
    _LOGGER.debug("Starting optimization update cycle")

    try:
        # Load sensor states and forecasts
        data = await self._load_data()
    except Exception as err:
        _LOGGER.error("Failed to load data: %s", err)
        raise UpdateFailed(f"Data loading failed: {err}") from err
```

**Data loading**:

```python
async def _load_data(self) -> dict[str, Any]:
    """Load all required data from Home Assistant."""
    data = {}

    # Load sensor states (e.g., battery SOC)
    for participant_id, config in self.config_entry.data["participants"].items():
        if config["type"] == "battery":
            soc_sensor = config["soc_sensor"]
            data[f"{participant_id}_soc"] = await self.sensor_loader.get_state(soc_sensor)

    # Load forecasts (e.g., prices, solar, load)
    for participant_id, config in self.config_entry.data["participants"].items():
        if "forecast" in config:
            forecast_sensors = config["forecast"]
            if not isinstance(forecast_sensors, list):
                forecast_sensors = [forecast_sensors]

            data[f"{participant_id}_forecast"] = await self.forecast_loader.get_forecast(
                forecast_sensors,
                horizon_hours=self.horizon_hours,
                period_minutes=self.period_minutes,
            )

    return data
```

### Step 2: Build Network Model

```python
async def _async_update_data(self) -> dict[str, Any]:
    # ... data loading ...

    try:
        # Build optimization network
        network = self._build_network(data)
    except Exception as err:
        _LOGGER.error("Failed to build network: %s", err)
        raise UpdateFailed(f"Network building failed: {err}") from err
```

**Network building**:

```python
def _build_network(self, data: dict[str, Any]) -> Network:
    """Build network model from configuration and data."""
    network = Network(
        name=self.config_entry.title,
        period=self.period,
        n_periods=self.n_periods,
    )

    # Create entities
    for participant_id, config in self.config_entry.data["participants"].items():
        entity = self._create_entity(participant_id, config, data)
        network.elements[participant_id] = entity

    # Create connections
    for conn_config in self.config_entry.data["connections"]:
        connection = Connection(
            name=f"{conn_config['source']}_to_{conn_config['target']}",
            period=self.period,
            n_periods=self.n_periods,
            source=conn_config["source"],
            target=conn_config["target"],
            min_power=conn_config.get("min_power"),
            max_power=conn_config.get("max_power"),
        )
        network.connections.append(connection)

    # Validate network
    network.validate()

    return network
```

### Step 3: Run Optimization

```python
async def _async_update_data(self) -> dict[str, Any]:
    # ... data loading and network building ...

    # Run optimization
    start_time = time.time()

    try:
        # Run optimization in executor (blocking operation)
        cost = await self.hass.async_add_executor_job(
            network.optimize,
            self.optimizer,
        )
        duration = time.time() - start_time
        status = "optimal"

        _LOGGER.info(
            "Optimization completed: cost=%.2f, duration=%.3fs",
            cost,
            duration,
        )

    except Exception as err:
        duration = time.time() - start_time
        status = "failed"

        _LOGGER.error("Optimization failed: %s", err)
        raise UpdateFailed(f"Optimization failed: {err}") from err
```

### Step 4: Extract Results

```python
async def _async_update_data(self) -> dict[str, Any]:
    # ... optimization ...

    # Extract results
    results = {
        "_network": {
            "cost": cost,
            "status": status,
            "duration": duration,
        }
    }

    # Extract entity results
    for entity_name, entity in network.elements.items():
        results[entity_name] = self._extract_entity_results(entity)

    return results


def _extract_entity_results(self, entity: Element) -> dict[str, Any]:
    """Extract optimization results from entity."""
    results = {}

    # Power results
    if entity.power_production:
        results["power_production"] = [
            value(var) if isinstance(var, LpVariable) else var
            for var in entity.power_production
        ]

    if entity.power_consumption:
        results["power_consumption"] = [
            value(var) if isinstance(var, LpVariable) else var
            for var in entity.power_consumption
        ]

    # Energy results (for batteries)
    if entity.energy:
        results["energy"] = [
            value(var) if isinstance(var, LpVariable) else var
            for var in entity.energy
        ]

    return results
```

### Step 5: Sensor Updates

Sensors are automatically updated via the coordinator pattern:

```python
class HaeoSensor(CoordinatorEntity, SensorEntity):
    """Sensor that gets data from coordinator."""

    def __init__(
        self,
        coordinator: HaeoDataUpdateCoordinator,
        entity_name: str,
        sensor_type: str,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self.entity_name = entity_name
        self.sensor_type = sensor_type

    @property
    def native_value(self) -> float | None:
        """Return current state from coordinator data."""
        if self.coordinator.data is None:
            return None

        entity_data = self.coordinator.data.get(self.entity_name, {})
        sensor_data = entity_data.get(self.sensor_type, [])

        # Return first value (current period)
        return sensor_data[0] if sensor_data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return forecast attribute."""
        if self.coordinator.data is None:
            return {}

        entity_data = self.coordinator.data.get(self.entity_name, {})
        sensor_data = entity_data.get(self.sensor_type, [])

        # Create forecast array with timestamps
        forecast = [
            {
                "datetime": self.coordinator.hass.loop.time() + i * self.coordinator.period * 3600,
                "value": value,
            }
            for i, value in enumerate(sensor_data)
        ]

        return {"forecast": forecast}
```

## Error Handling

### Data Loading Errors

```python
async def _load_data(self) -> dict[str, Any]:
    """Load data with error handling."""
    try:
        # Load data...
        pass
    except EntityNotFound as err:
        _LOGGER.warning("Sensor not found: %s", err)
        raise UpdateFailed(f"Required sensor not found: {err}") from err
    except ForecastNotAvailable as err:
        _LOGGER.warning("Forecast not available: %s", err)
        raise UpdateFailed(f"Forecast data unavailable: {err}") from err
```

### Optimization Errors

```python
try:
    cost = network.optimize(self.optimizer)
except InfeasibleError as err:
    _LOGGER.error("Optimization infeasible: %s", err)
    # Return last known good state or partial results
    raise UpdateFailed("Network constraints cannot be satisfied") from err
except SolverError as err:
    _LOGGER.error("Solver error: %s", err)
    raise UpdateFailed(f"Solver failed: {err}") from err
```

### Graceful Degradation

When errors occur:

1. Log error details
2. Raise `UpdateFailed` exception
3. Coordinator marks data as unavailable
4. Sensors show "unavailable" state
5. Next update cycle tries again

## Performance Optimization

### Executor Usage

Optimization is CPU-intensive, so it runs in executor:

```python
# Run in executor thread pool
cost = await self.hass.async_add_executor_job(
    network.optimize,
    self.optimizer,
)
```

This prevents blocking the event loop.

### Caching

Coordinator caches results until next update:

```python
# Access cached data
current_data = coordinator.data

# No need to re-fetch unless update triggered
```

### Update Interval

Fixed at initialization, not user-configurable:

```python
update_interval = timedelta(minutes=period_minutes)
```

**Why fixed?**: Follows Home Assistant best practices - polling frequency should be determined by integration, not user.

## Testing Coordinator

### Unit Tests

```python
async def test_coordinator_init(hass, mock_config_entry):
    """Test coordinator initialization."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_config_entry)

    assert coordinator.horizon_hours == 48
    assert coordinator.period_minutes == 5
    assert coordinator.n_periods == 576


async def test_coordinator_update(hass, mock_config_entry, mock_loaders):
    """Test coordinator update cycle."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_config_entry)

    # Trigger update
    await coordinator.async_refresh()

    # Verify results
    assert coordinator.data is not None
    assert "_network" in coordinator.data
    assert coordinator.data["_network"]["status"] == "optimal"
```

### Integration Tests

```python
async def test_full_update_cycle(hass, initialized_entry):
    """Test complete update cycle."""
    coordinator = hass.data[DOMAIN][initialized_entry.entry_id]

    # Trigger update
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # Check sensors updated
    cost_sensor = hass.states.get("sensor.network_optimization_cost")
    assert cost_sensor.state not in ("unknown", "unavailable")
```

## Related Documentation

- [Architecture](architecture.md) - How coordinator fits into system
- [Testing](testing.md) - Testing coordinator
- [Sensors](../user-guide/sensors.md) - Sensor updates

## Next Steps

- Review coordinator implementation in `coordinator.py`
- Study data loader implementations in `data/loader/`
- Understand sensor update mechanism in `sensor.py`

[:octicons-arrow-right-24: Return to Architecture Overview](architecture.md)
