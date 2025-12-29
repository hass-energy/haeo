# Phase 3: Refactor NetworkOptimizationCoordinator

## Goal

Modify the network coordinator to read input values from HAEO input entities instead of loading directly from external sensors. This completes the separation of input loading from optimization.

## Prerequisites

- Phase 1 complete (input entities exist)
- Phase 2 complete (element coordinators manage input values)

## Deliverables

1. `coordinator/network_coordinator.py` - Refactored to read from input entities
2. Updated sensor platform to use new coordinator location
3. Deprecate/remove direct sensor loading in network coordinator

## Implementation Details

### 1. Query Input Entities from Registry

```python
def _get_input_entity_values(
    self,
    hass: HomeAssistant,
    config_entry_id: str,
) -> dict[str, dict[str, Any]]:
    """Get current values from input entities.

    Returns: {subentry_id: {field_name: value_or_list}}
    """
    er = entity_registry.async_get(hass)

    # Get all entities for this config entry
    entries = er.entities.get_entries_for_config_entry_id(config_entry_id)

    result: dict[str, dict[str, Any]] = {}

    for entry in entries:
        # Filter to number and switch platforms (input entities)
        if entry.domain not in ("number", "switch"):
            continue

        # Get subentry ID from registry entry
        if not entry.config_subentry_id:
            continue

        # Get current state
        state = hass.states.get(entry.entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            continue

        # Extract field name from unique_id pattern: {entry_id}_{subentry_id}_{field_name}
        parts = entry.unique_id.split("_", 2) if entry.unique_id else []
        if len(parts) < 3:
            continue
        field_name = parts[2]

        # Get value and forecast from state
        if entry.domain == "number":
            value = float(state.state)
            forecast = state.attributes.get("forecast", [])
            if forecast:
                values = [point["value"] for point in forecast]
            else:
                values = [value]
        else:  # switch
            values = state.state == STATE_ON

        # Store by subentry
        if entry.config_subentry_id not in result:
            result[entry.config_subentry_id] = {}
        result[entry.config_subentry_id][field_name] = values

    return result
```

### 2. Refactor \_async_update_data

Instead of calling `load_element_configs()` which loads from external sensors:

```python
async def _async_update_data(self) -> CoordinatorData:
    """Run optimization cycle."""

    # Get values from input entities instead of loading directly
    input_values = self._get_input_entity_values(self.hass, self.config_entry.entry_id)

    # Build ConfigData from input entity values
    loaded_configs: dict[str, ElementConfigData] = {}

    for element_name, element_schema in self._participant_configs.items():
        # Find matching subentry by name
        subentry = self._get_subentry_by_name(element_name)
        if not subentry:
            continue

        subentry_inputs = input_values.get(subentry.subentry_id, {})

        # Build ConfigData from input values
        config_data = self._build_config_data(element_schema, subentry_inputs)
        loaded_configs[element_name] = config_data

    # Continue with existing optimization logic...
    network = await self.hass.async_add_executor_job(
        load_network,
        loaded_configs,
        forecast_timestamps,
    )

    # ... rest of optimization
```

### 3. Handle Initialization Order

The network coordinator may start before input entities are registered:

```python
async def _async_update_data(self) -> CoordinatorData:
    """Run optimization cycle."""

    # Check if input entities are ready
    input_values = self._get_input_entity_values(self.hass, self.config_entry.entry_id)

    if not input_values:
        # Entities not yet registered, schedule retry
        if not self._entities_ready:
            _LOGGER.debug("Input entities not ready, waiting...")
            # Don't fail, just return empty data and wait for entity registration
            # The element coordinators will trigger a refresh when ready
            raise UpdateFailed("Input entities not yet registered")

    self._entities_ready = True
    # ... continue with optimization
```

Alternative: Use `hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, ...)` to delay first refresh.

### 4. Track Input Entity Changes

Instead of tracking external sensor IDs, track our input entity IDs:

```python
def _setup_input_entity_tracking(self) -> None:
    """Set up tracking for input entity state changes."""
    er = entity_registry.async_get(self.hass)
    entries = er.entities.get_entries_for_config_entry_id(self.config_entry.entry_id)

    input_entity_ids = [
        entry.entity_id for entry in entries if entry.domain in ("number", "switch") and entry.config_subentry_id
    ]

    if input_entity_ids:
        self._input_entity_unsub = async_track_state_change_event(
            self.hass,
            input_entity_ids,
            self._handle_input_change,
        )


@callback
def _handle_input_change(self, event: Event[EventStateChangedData]) -> None:
    """Handle input entity state change."""
    self.hass.async_create_task(self.async_request_refresh())
```

### 5. Move Coordinator to Submodule

Move coordinator.py to coordinator/network_coordinator.py and update imports:

```
custom_components/haeo/coordinator/
├── __init__.py              # Re-exports
├── element_coordinator.py   # Per-subentry input coordinator
└── network_coordinator.py   # Optimization coordinator
```

## Robustness Considerations

### Entity ID Changes

Users can rename entity IDs. Track by unique_id via registry instead of entity_id:

```python
# Don't do this:
entity_id = "number.haeo_battery_capacity"

# Do this:
er = entity_registry.async_get(hass)
entry = er.async_get_entity_id("number", DOMAIN, unique_id)
```

### Missing Entities

Handle gracefully when entities are unavailable:

```python
if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
    _LOGGER.warning("Input entity %s unavailable", entity_id)
    # Use fallback or skip this element
```

### Concurrent Updates

Use debouncer to coalesce rapid input changes:

```python
# Already in existing coordinator
request_refresh_debouncer = Debouncer(hass, _LOGGER, cooldown=debounce_seconds, immediate=True)
```

## Testing Considerations

- Test reading values from input entities
- Test handling of unavailable entities
- Test entity ID rename scenarios
- Test initialization order (entities registered after coordinator starts)
- Test debouncing of rapid input changes

## Acceptance Criteria

1. Network coordinator reads from input entities, not external sensors
2. Handles initialization order gracefully
3. Tracks input entity state changes for refresh triggers
4. Works with renamed entity IDs (uses registry lookup)
5. Handles unavailable entities gracefully
6. Existing optimization logic unchanged

## Notes for Future Phases

- Phase 4 will remove echoed inputs from model outputs
- The `_build_config_data` method bridges input entity values to ConfigData format
