# HAEO Input/Output Separation Refactor

## Overview

This refactor separates input loading from output generation by introducing input entities (NumberEntity/SwitchEntity) that act as an intermediate layer between external sensors and the optimization model.

## Current Architecture

```
External Sensors → TimeSeriesLoader → Model → Outputs (including echoed inputs)
```

## Target Architecture

```
External Sensors → ElementInputCoordinator → Input Entities
                                                    ↓
                          NetworkOptimizationCoordinator → Model → Output Sensors
```

## Key Benefits

1. **User Control**: Users can manually set inputs via number/switch entities
2. **Observability**: All optimization inputs are visible as entities
3. **Decoupling**: Input loading is independent of optimization timing
4. **Clean Outputs**: Model outputs only contain computed values, not echoed inputs

## Phases

| Phase                                       | Description                                 | Status      |
| ------------------------------------------- | ------------------------------------------- | ----------- |
| [Phase 1](01-input-entities.md)             | Create input entity infrastructure          | Not Started |
| [Phase 2](02-element-coordinator.md)        | Create per-subentry ElementInputCoordinator | Not Started |
| [Phase 3](03-network-coordinator.md)        | Refactor NetworkOptimizationCoordinator     | Not Started |
| [Phase 4](04-remove-echoed-inputs.md)       | Remove echoed inputs from model outputs     | Not Started |
| [Phase 5](05-coordinator-data-structure.md) | Update CoordinatorData structure            | Not Started |

## Key Design Decisions

### Multi-Hub Safety

All entity unique IDs include `config_entry.entry_id`:

```python
unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{field_name}"
```

### Entity-Subentry Association

Use HA's built-in subentry tracking:

```python
async_add_entities(entities, config_subentry_id=subentry.subentry_id)
```

### Initialization Order Robustness

NetworkOptimizationCoordinator queries entity registry and handles missing entities gracefully:

1. Query registry for entities with matching `config_entry_id`
2. If entities not found, wait for `EVENT_HOMEASSISTANT_STARTED` or retry
3. Track entities by registry entry (handles renamed entity IDs)

### Coordinator Communication

ElementInputCoordinator notifies NetworkOptimizationCoordinator via callback when inputs change:

```python
# In ElementInputCoordinator
self._on_input_change_callback()

# In NetworkOptimizationCoordinator
await self.async_request_refresh()
```

## Files Overview

### New Files

- `custom_components/haeo/coordinator/__init__.py` - Coordinator module exports
- `custom_components/haeo/coordinator/element_coordinator.py` - Per-subentry input coordinator
- `custom_components/haeo/coordinator/network_coordinator.py` - Optimization coordinator (moved from coordinator.py)
- `custom_components/haeo/entities/__init__.py` - Entity module exports
- `custom_components/haeo/entities/haeo_number.py` - Input number entity
- `custom_components/haeo/entities/haeo_switch.py` - Input switch entity
- `custom_components/haeo/number.py` - NUMBER platform setup
- `custom_components/haeo/switch.py` - SWITCH platform setup
- `custom_components/haeo/schema/input_fields.py` - Input field metadata

### Modified Files

- `custom_components/haeo/__init__.py` - Runtime data structure, platform registration
- `custom_components/haeo/coordinator.py` - Becomes thin wrapper/re-exports
- `custom_components/haeo/sensors/sensor.py` - Navigate new data structure
- `custom_components/haeo/diagnostics.py` - Use new data structure
- `custom_components/haeo/model/power_connection.py` - Remove echoed outputs
- `custom_components/haeo/elements/*.py` - Remove echoed outputs from adapters
- `custom_components/haeo/translations/en.json` - Add input entity translations
