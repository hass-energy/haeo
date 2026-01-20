---
name: Optimization Control Features
overview: Add a switch to enable/disable automatic optimization and a service to manually trigger optimization. The switch will be on the network device and defaults to enabled. The service will bypass debouncing for immediate execution.
todos: []
---

# Optimization Control Features

## Overview

Add two features to give users control over when optimization runs:

1. A switch entity to enable/disable automatic optimization
2. A service to manually trigger optimization on demand

## Implementation

### 1. Automatic Optimization Switch

**New entity**: Create `HaeoAutoOptimizeSwitch` in [`custom_components/haeo/entities/haeo_auto_optimize_switch.py`](custom_components/haeo/entities/haeo_auto_optimize_switch.py)

- Standalone switch entity (not tied to element subentries like existing `HaeoInputSwitch`)
- Attached to the network device
- Translation key: `network_auto_optimize`
- Uses coordinator's new property to control optimization triggering
- Default: enabled (preserves current behavior)
- Entity category: CONFIG

**Coordinator changes** in [`custom_components/haeo/coordinator/coordinator.py`](custom_components/haeo/coordinator/coordinator.py):

- Add `auto_optimize_enabled: bool` property (defaults to `True`)
- Modify `_trigger_optimization()` to check this flag before scheduling optimization
- Add `async_run_optimization()` method for manual trigger (bypasses debouncing and auto-optimize check)

**Switch platform** in [`custom_components/haeo/switch.py`](custom_components/haeo/switch.py):

- Add creation of `HaeoAutoOptimizeSwitch` for the network subentry

### 2. Run Optimizer Service

**Service registration** in [`custom_components/haeo/services.py`](custom_components/haeo/services.py):

- Add `run_optimizer` service handler
- Takes `config_entry` parameter (same pattern as `save_diagnostics`)
- Calls `coordinator.async_run_optimization()` directly

**Service definition** in [`custom_components/haeo/services.yaml`](custom_components/haeo/services.yaml):

- Add `run_optimizer` service with config entry selector

### 3. Translations

**Update** [`custom_components/haeo/translations/en.json`](custom_components/haeo/translations/en.json):

- Add `entity.switch.network_auto_optimize` for the switch name
- Add `services.run_optimizer` for service name and description

## Files Changed

| File                                    | Change                                                                     |
| --------------------------------------- | -------------------------------------------------------------------------- |
| `coordinator/coordinator.py`            | Add `auto_optimize_enabled` property and `async_run_optimization()` method |
| `entities/haeo_auto_optimize_switch.py` | New file for auto-optimize switch entity                                   |
| `switch.py`                             | Create auto-optimize switch for network subentry                           |
| `services.py`                           | Add `run_optimizer` service handler                                        |
| `services.yaml`                         | Add `run_optimizer` service definition                                     |
| `translations/en.json`                  | Add switch and service translations                                        |
