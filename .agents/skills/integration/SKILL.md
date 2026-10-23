---
name: integration
description: Home Assistant integration patterns — the event-driven optimization coordinator in coordinator/, HaeoRuntimeData and setup and unload in __init__.py, input stores and the inputs/ package of Home Assistant readers, entity unique IDs and naming, device registry, exception types, and diagnostics redaction. Use when working anywhere under custom_components/haeo/ outside the standalone core package.
---

# Home Assistant integration development

## Package boundary

`core/` never imports Home Assistant; import-linter enforces it.
Code that reads Home Assistant at run time lives outside it: the `inputs/` package holds the state machine adapter, calendar event loading, and meter history readers that feed the core loaders.

## Coordinator pattern

`HaeoDataUpdateCoordinator` in [`coordinator/coordinator.py`](../../../custom_components/haeo/coordinator/coordinator.py) assembles each element's config from the input stores, runs the optimization, and exposes the results.

- It has no `update_interval`.
    Updates are event-driven: input store changes and horizon changes signal the results stale, and the coordinator optimizes after the hub's debounce window.
- Refreshes are single-flight: one lock and one "rerun wanted" flag, so requests made while an optimization runs share one follow-up run.
    `async_request_refresh()` goes through the debounce window like any automatic request.
- An optimization is skipped while forecast inputs are still loading for a new horizon; `async_run_optimization()`, behind the `haeo.optimize` action, checks this under the lock and raises `HomeAssistantError` with `inputs_not_aligned`.
- Turning auto-optimize off cancels an optimization waiting out the debounce window.
- Raise `UpdateFailed` for data loading or optimization errors, or `ReportedUpdateFailed` when the failure raises a repair issue of its own.

## Entity development

### Unique IDs

Every entity and device ID is built and parsed through `custom_components/haeo/unique_id.py`, never formatted or split by hand:

```python
self._attr_unique_id = element_unique_id(config_entry.entry_id, subentry.subentry_id, unique_key)
```

Element IDs are `{entry_id}_{subentry_id}_{key}` and hub IDs are `{entry_id}_{key}`.
`parse_element_unique_id` reads an element ID back, so generation, device cleanup, and migrations all agree on the format.
Migrations of formats that have shipped keep their own historic parsing.

Acceptable sources: config entry ID, subentry ID, device serial numbers.
Never use: IP addresses, hostnames, user-provided names.

### Subentry links

Add entities with `async_add_entities(entities, config_subentry_id=subentry.subentry_id)`, one call per subentry.
Element entities link to their element's subentry and hub entities to the network subentry, matching their devices.
Home Assistant then removes the entities when the subentry is deleted.

### Entity naming

Use translation keys for all entity names:

```python
class MySensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "battery_power_charge"
```

### State handling

- Use `None` for unknown values (not "unknown" string)
- Implement `available` property for availability

### Event lifecycle

```python
async def async_added_to_hass(self) -> None:
    """Subscribe to events."""
    self.async_on_remove(self.coordinator.async_add_listener(self._handle_update))
```

## Device registry

Create devices through the helpers in `entities/device.py`, which register each device with the adapter's device name as its translation key and the element name as the `name` placeholder.

## Exception handling

All exceptions that may reach the user must use Home Assistant exception types with translations.
Never raise generic exceptions that would show "unknown error" in the UI.

Setup never fails permanently, so that HAEO recovers on its own once the conditions it depends on settle.
`async_setup_entry` turns any unexpected error into `ConfigEntryNotReady` with a `setup_failed` repair issue; never raise `ConfigEntryError`.

- `ConfigEntryNotReady`: Setup cannot finish yet; Home Assistant retries it
- `UpdateFailed`: Data loading or optimization errors
- `HomeAssistantError`: User-facing errors with translation support

For service calls and user actions, use `HomeAssistantError` with a translation key:

```python
raise HomeAssistantError(
    translation_domain=DOMAIN,
    translation_key="inputs_not_aligned",
)
```

## Diagnostics

Diagnostics are collected in [`diagnostics/collector.py`](../../../custom_components/haeo/diagnostics/collector.py), which passes config through `async_redact_data` with `_REDACTED_CONFIG_KEYS`.
Add any key that holds a password, token, or sensitive coordinate there.

## Setup and unload

`async_setup_entry()` in [`__init__.py`](../../../custom_components/haeo/__init__.py) stores a `HaeoRuntimeData` on `entry.runtime_data`, holding the horizon manager, the input stores in `input_stores`, the auto-optimize switch, and the coordinator.
Setup runs in this order:

1. Create the horizon manager and the input stores, and start the loaders that keep the stores loaded.
2. Forward the input platforms, which only display the stores, and wait for every input store to settle, raising `ConfigEntryNotReady` while inputs are unavailable.
3. Initialize the coordinator and run the first optimization with `async_refresh()`, so a failed optimization does not retry setup.
4. Forward the output platforms.

Register every cleanup with `entry.async_on_unload()` during setup.
`async_unload_entry()` then only unloads the platforms, clears `entry.runtime_data` if they unloaded, and returns that result.
