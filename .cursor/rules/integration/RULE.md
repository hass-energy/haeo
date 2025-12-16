---
description: "Home Assistant integration patterns"
globs: ["custom_components/haeo/**"]
alwaysApply: false
---

# Home Assistant integration development

## Coordinator pattern

Use DataUpdateCoordinator for data management:

```python
class MyCoordinator(DataUpdateCoordinator[MyData]):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
            config_entry=config_entry,  # Always pass config_entry
        )

    async def _async_update_data(self) -> MyData:
        try:
            return await self._fetch_data()
        except ApiError as err:
            raise UpdateFailed(f"API error: {err}") from err
```

- Pass `config_entry` to coordinator constructor
- Use `UpdateFailed` for API errors
- Use `ConfigEntryAuthFailed` for auth issues
- Integration determines update interval (not user-configurable)

## Entity development

### Unique IDs

Every entity must have a unique ID:
```python
self._attr_unique_id = f"{entry.entry_id}-{element_id}-power"
```

Acceptable sources: config entry ID, device serial numbers, MAC addresses.
Never use: IP addresses, hostnames, device names.

### Entity naming

```python
class MySensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "battery_power"  # Use translation keys
```

### State handling

- Use `None` for unknown values (not "unknown" string)
- Implement `available` property for availability

### Event lifecycle

```python
async def async_added_to_hass(self) -> None:
    """Subscribe to events."""
    self.async_on_remove(
        self.coordinator.async_add_listener(self._handle_update)
    )
```

## Device registry

Group related entities under devices:

```python
_attr_device_info = DeviceInfo(
    identifiers={(DOMAIN, device_id)},
    name=device_name,
    manufacturer="HAEO",
)
```

## Diagnostics

Implement diagnostic data collection:

```python
TO_REDACT = [CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE]

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    return async_redact_data(entry.data, TO_REDACT)
```

Never expose passwords, tokens, or sensitive coordinates.

## Setup and unload

```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from config entry."""
    coordinator = MyCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

## Exception types

- `ConfigEntryNotReady`: Device offline or temporary failure
- `ConfigEntryAuthFailed`: Authentication problems
- `ConfigEntryError`: Unresolvable setup problems
- `UpdateFailed`: API errors during coordinator update
