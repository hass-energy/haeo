---
name: Auto-optimize as Input
overview: Refactor the auto-optimize switch to be a true input entity created in switch.py, with the coordinator reading from it instead of the switch pushing state to the coordinator.
todos:
  - id: create-switch-entity
    content: Create entities/auto_optimize_switch.py with simplified AutoOptimizeSwitch class
    status: pending
  - id: update-runtime-data
    content: Add auto_optimize_switch field to HaeoRuntimeData in __init__.py
    status: pending
  - id: update-switch-platform
    content: Add auto-optimize switch creation to switch.py
    status: pending
  - id: update-coordinator
    content: Refactor coordinator to read from switch and subscribe to state changes
    status: pending
  - id: cleanup-init
    content: Remove manual switch creation from __init__.py
    status: pending
  - id: delete-old-file
    content: Delete entities/haeo_auto_optimize_switch.py
    status: pending
  - id: update-exports
    content: Update entities/__init__.py exports
    status: pending
isProject: false
---

# Auto-optimize Switch as Input Entity

## Current Problem

The auto-optimize switch breaks the normal entity pattern:

- Created in `__init__.py` after coordinator exists (lines 216-232)
- Pushes state to coordinator (`coordinator.auto_optimize_enabled = True`)
- Requires special handling outside normal platform setup

## New Approach

Treat the auto-optimize switch as a true input entity:

- Created in `switch.py` like other switches (no coordinator reference needed)
- Coordinator pulls state from the switch and subscribes to changes
- Follows the same lifecycle as other input entities

## Architecture

```mermaid
flowchart LR
    subgraph before [Current: Switch pushes to Coordinator]
        switch1[AutoOptimizeSwitch] -->|"sets auto_optimize_enabled"| coord1[Coordinator]
        switch1 -->|"calls async_run_optimization"| coord1
    end

    subgraph after [New: Coordinator pulls from Switch]
        switch2[AutoOptimizeSwitch] -->|"fires state change"| ha[Home Assistant]
        ha -->|"event"| coord2[Coordinator]
        coord2 -->|"reads is_on"| switch2
    end
```



## Changes

### 1. Refactor entity: `entities/auto_optimize_switch.py`

Rename from `haeo_auto_optimize_switch.py` and simplify:

- Remove coordinator dependency from constructor
- Remove coordinator imports
- Keep `RestoreEntity` for state persistence
- `async_turn_on/off` just update state (no coordinator calls)
- Store reference to `runtime_data` to trigger coordinator refresh on turn-on

```python
class AutoOptimizeSwitch(SwitchEntity, RestoreEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: HaeoConfigEntry,
        device_entry: DeviceEntry,
    ) -> None:
        # No coordinator reference needed
        ...

    async def async_turn_on(self, **_kwargs: Any) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()
        # Trigger coordinator refresh if it exists
        runtime_data = self._config_entry.runtime_data
        if runtime_data and runtime_data.coordinator:
            await runtime_data.coordinator.async_run_optimization()
```

### 2. Update `switch.py`

Add auto-optimize switch creation after input switches:

- Find network subentry (like `__init__.py` does)
- Create `AutoOptimizeSwitch` linked to network device
- Store in `runtime_data` for coordinator access (new field: `auto_optimize_switch`)

### 3. Update `HaeoRuntimeData` in `__init__.py`

Add field for the auto-optimize switch:

```python
@dataclass(slots=True)
class HaeoRuntimeData:
    horizon_manager: HorizonManager
    input_entities: dict[tuple[str, str], HaeoInputNumber | HaeoInputSwitch] = field(default_factory=dict)
    coordinator: HaeoDataUpdateCoordinator | None = field(default=None)
    auto_optimize_switch: AutoOptimizeSwitch | None = field(default=None)  # NEW
    value_update_in_progress: bool = field(default=False)
```

### 4. Update coordinator

In `coordinator/coordinator.py`:

- Remove `_auto_optimize_enabled` internal state
- Add property that reads from switch: `runtime_data.auto_optimize_switch.is_on`
- Subscribe to switch state changes in `async_initialize()`
- On switch turn-on event: resume horizon manager
- On switch turn-off event: pause horizon manager

### 5. Clean up `__init__.py`

Remove lines 216-232 (manual switch creation and platform injection).

### 6. Delete old file

Delete `entities/haeo_auto_optimize_switch.py`.

## File Summary


| File                                    | Action                                            |
| --------------------------------------- | ------------------------------------------------- |
| `entities/auto_optimize_switch.py`      | Create (renamed, simplified)                      |
| `entities/haeo_auto_optimize_switch.py` | Delete                                            |
| `switch.py`                             | Add auto-optimize switch creation                 |
| `__init__.py`                           | Add field to runtime data, remove manual creation |
| `coordinator/coordinator.py`            | Read from switch, subscribe to changes            |
| `entities/__init__.py`                  | Update exports                                    |
