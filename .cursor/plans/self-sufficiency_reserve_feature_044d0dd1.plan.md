---
name: Required Energy Sensor
overview: Add a "Required Energy" calculation to the data loading layer, making it available to the optimization algorithm and exposing it as a sensor.
todos:
  - id: const-output
    content: Add NETWORK_REQUIRED_ENERGY output name constant to const.py
    status: completed
  - id: calculate-required
    content: Add required energy calculation function in data/__init__.py
    status: completed
  - id: network-store
    content: Store required_energy on Network object so model elements can access it
    status: completed
  - id: coordinator
    content: Include required energy in CoordinatorData after optimization
    status: completed
  - id: sensor
    content: Add required energy sensor entity to sensor.py
    status: completed
  - id: tests
    content: Add tests for required energy calculation
    status: completed
  - id: translations
    content: Add translation strings for new sensor
    status: completed
---

# Required Energy Sensor

Reference: [GitHub Issue #60](https://github.com/hass-energy/haeo/issues/60)

## Overview

Add a **Required Energy** calculation to the data loading layer. This value represents the total future energy required from dispatchable sources (battery, grid, generator) to satisfy upcoming fixed loads.

**Key architectural requirement:** The calculation happens BEFORE optimization so that model elements (e.g., batteries) can use it as input for constraints. It is also exposed as a sensor output for user visibility.

## Primary Use Case: Dynamic Battery Reserve

The required energy can be used as a **dynamic minimum reserve level** for a battery. By setting the battery's minimum state-of-charge equal to the required energy, the system can:

- Ensure the battery **retains enough energy** to cover future load that uncontrollable sources cannot meet
- **Release** stored energy only when doing so will not jeopardize future demand
- Avoid overly aggressive discharge early in the day when requirements are still ahead

## Algorithm

### Step 1: Calculate Net Forecasted Power Per Interval

```
net_power[t] = uncontrollable_generation[t] - load_forecast[t]
```

Where `uncontrollable_generation` includes solar (and future: wind, etc.)

- Positive → generation surplus
- Negative → requires dispatchable energy

### Step 2: Extract Required Energy Per Interval

Only count intervals where load exceeds uncontrollable generation:

```
required[t] = max(0, -net_power[t]) * period[t]  # kWh
```

### Step 3: Reverse Cumulative Sum

Compute the reverse cumulative sum so each time point reflects:

*"From this moment forward, this is the amount of energy required from dispatchable sources."*

```python
# For each timestep, sum required energy from t to end of horizon
required_energy[t] = sum(required[i] for i in t..T)
```

### Resulting Behaviour

At any timestamp `t`, the value represents:

**"Energy required from now until the end of the forecast horizon that must come from dispatchable sources (battery, grid, generator)."**

The value naturally:

- Drops to zero when future uncontrollable generation covers all remaining load
- Rises when upcoming fixed loads exceed forecasted generation
- Decreases over time as requirements are met

## Example

| Time | Load | Solar | Net Power | Required (interval) | Required Energy (cumulative) |

|\------|------|-------|-----------|---------------------|------------------------------|

| 6pm | 2 kW | 0 kW | -2 kW | 4 kWh (2h) | 11 kWh |

| 8pm | 1 kW | 0 kW | -1 kW | 4 kWh (4h) | 7 kWh |

| 12am | 0.5 kW | 0 kW | -0.5 kW | 3 kWh (6h) | 3 kWh |

| 6am | 1 kW | 2 kW | +1 kW | 0 kWh | 0 kWh |

| 10am | 1 kW | 5 kW | +4 kWh | 0 kWh | 0 kWh |

At 6pm, you need **11 kWh** from dispatchable sources to meet load until solar returns.

## Architecture

The required energy is calculated in the **data loading layer** (before optimization) so that:

1. Model elements can use it as input for constraints
2. It can be exposed as a sensor output after optimization

```mermaid
flowchart TD
    subgraph DataLoading [Data Loading Layer - BEFORE Optimization]
        LoadConfigs[Load Element Configs]
        CalcRequired[calculate_required_energy]
        Network[Network Object]
    end

    subgraph Optimization [Optimization Layer]
        Battery[Battery Element]
        Constraints[Future: Reserve Constraints]
    end

    subgraph Output [After Optimization]
        CoordData[CoordinatorData]
        Sensor["sensor.haeo_hub_required_energy"]
    end

    LoadConfigs --> CalcRequired
    CalcRequired -->|"required_energy[]"| Network
    Network -->|"network.required_energy"| Battery
    Battery -.->|"Future: use for min SOC"| Constraints
    Network --> CoordData
    CoordData --> Sensor
```

## Key Files to Modify

1. **[`custom_components/haeo/const.py`](custom_components/haeo/const.py)** - Add `NETWORK_REQUIRED_ENERGY` output name

2. **[`custom_components/haeo/data/__init__.py`](custom_components/haeo/data/__init__.py)** - Add `calculate_required_energy()` function

3. **[`custom_components/haeo/model/network.py`](custom_components/haeo/model/network.py)** - Add `required_energy` field to Network dataclass

4. **[`custom_components/haeo/coordinator.py`](custom_components/haeo/coordinator.py)** - Include required energy in `CoordinatorData`

5. **[`custom_components/haeo/sensor.py`](custom_components/haeo/sensor.py)** - Add `HaeoRequiredEnergySensor` entity

6. **[`custom_components/haeo/translations/en.json`](custom_components/haeo/translations/en.json)** - Add translation strings

## Implementation Details

### Constants (`const.py`)

```python
# Add to NetworkOutputName type
type NetworkOutputName = Literal[
    "network_optimization_cost",
    "network_required_energy",  # NEW
]

NETWORK_REQUIRED_ENERGY: Final = "network_required_energy"
```

### Required Energy Calculation (`data/__init__.py`)

```python
def calculate_required_energy(
    participants: Mapping[str, ElementConfigData],
    periods_hours: Sequence[float],
) -> list[float]:
    """Calculate the required energy at each timestep.

    This is calculated BEFORE optimization so model elements can use it.

    Returns:
        List of required energy values (kWh) at each timestep boundary (n_periods + 1).
        Each value represents the total energy required from dispatchable sources
        from that point until the end of the horizon.
    """
    n_periods = len(periods_hours)

    # Aggregate all load forecasts
    total_load = np.zeros(n_periods)
    for config in participants.values():
        if config["element_type"] == "load":
            total_load += np.array(config["forecast"])

    # Aggregate all uncontrollable generation (solar, future: wind, etc.)
    total_uncontrollable = np.zeros(n_periods)
    for config in participants.values():
        if config["element_type"] == "solar":
            total_uncontrollable += np.array(config["forecast"])

    # Calculate net power (positive = surplus, negative = requires dispatchable)
    net_power = total_uncontrollable - total_load

    # Extract only requirements (negative values become positive energy requirements)
    required_power = np.maximum(0, -net_power)  # kW
    required_interval = required_power * np.array(periods_hours)  # kWh

    # Reverse cumulative sum: how much required energy from t to end
    required_energy = np.cumsum(required_interval[::-1])[::-1]

    # Add terminal zero (at end of horizon, no future requirement)
    required_energy = np.concatenate([required_energy, [0.0]])

    return required_energy.tolist()
```

### Network Model (`model/network.py`)

Add `required_energy` as an optional field that's set during network construction:

```python
@dataclass
class Network:
    """Network class for electrical system modeling."""

    name: str
    periods: Sequence[float]
    elements: dict[str, Element[Any, Any]] = field(default_factory=dict)
    required_energy: Sequence[float] | None = None  # NEW: Available to model elements
    _solver: Highs = field(default_factory=Highs, repr=False)
```

### Data Loading (`data/__init__.py`)

In `load_network()`, calculate and pass to Network:

```python
async def load_network(
    entry: ConfigEntry,
    *,
    periods_seconds: Sequence[int],
    participants: Mapping[str, ElementConfigData],
) -> Network:
    # ... existing code ...
    periods_hours = [s / 3600 for s in periods_seconds]

    # Calculate required energy BEFORE building network
    required_energy = calculate_required_energy(participants, periods_hours)

    # Build network with required_energy available
    net = Network(
        name=f"haeo_network_{entry.entry_id}",
        periods=periods_hours,
        required_energy=required_energy,  # NEW
    )

    # ... rest of existing code ...
```

### Coordinator (`coordinator.py`)

After optimization, include in `CoordinatorData`:

```python
@dataclass
class CoordinatorData:
    # ... existing fields ...
    required_energy: list[float]  # kWh at each timestep boundary
```

In `_async_update_data()`:

```python
# After network.optimize()
return CoordinatorData(
    # ... existing fields ...
    required_energy=list(network.required_energy),
)
```

### Sensor Entity (`sensor.py`)

```python
class HaeoRequiredEnergySensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the current required energy from dispatchable sources."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float:
        """Return the current required energy (first timestep)."""
        return self.coordinator.data.required_energy[0]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the full required energy forecast as an attribute."""
        return {
            "forecast": self.coordinator.data.required_energy,
        }
```

## Future Use by Optimization

With `required_energy` stored on the Network object, future enhancements can access it from model elements:

```python
# In Battery.build_constraints() - FUTURE
def build_constraints(self) -> None:
    # ... existing constraints ...

    # Future: Use network's required_energy for dynamic reserve
    if self._network.required_energy is not None:
        # Distribute by capacity and add reserve constraint
        ...
```

This architecture ensures the calculation is done once, stored centrally, and accessible to both:

- Model elements (for constraints)
- Sensor output (for user visibility)
