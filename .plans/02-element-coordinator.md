# Phase 2: Create Per-Subentry ElementInputCoordinator

## Goal

Create a per-subentry coordinator that manages input entity values, tracks source entities for driven mode, and notifies the network coordinator when inputs change.

## Prerequisites

- Phase 1 complete (input entities exist)

## Deliverables

1. `coordinator/__init__.py` - Module exports
2. `coordinator/element_coordinator.py` - ElementInputCoordinator class
3. Updated `__init__.py` - Create element coordinators per subentry

## Implementation Details

### 1. ElementInputCoordinator (`coordinator/element_coordinator.py`)

```python
@dataclass(slots=True)
class ElementInputData:
    """Data for a single element's inputs."""

    field_values: dict[str, list[float] | float | bool]  # field_name -> values
    forecast_timestamps: tuple[float, ...]


class ElementInputCoordinator(DataUpdateCoordinator[ElementInputData]):
    """Per-subentry coordinator managing input entity values.

    This coordinator:
    1. Tracks source entity state changes for driven fields
    2. Loads and interpolates forecast data from source entities
    3. Provides current values to input entities
    4. Notifies network coordinator when inputs change
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        subentry: ConfigSubentry,
        on_input_change: Callable[[], None],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"HAEO Element {subentry.title}",
            update_interval=None,  # Event-driven only, no polling
        )

        self._config_entry = config_entry
        self._subentry = subentry
        self._on_input_change = on_input_change

        # Collect source entity IDs from config
        self._source_entity_ids: set[str] = set()
        self._field_sources: dict[str, list[str]] = {}  # field_name -> entity_ids

        for field_name, value in subentry.data.items():
            entity_ids = self._extract_entity_ids(value)
            if entity_ids:
                self._field_sources[field_name] = entity_ids
                self._source_entity_ids.update(entity_ids)

        # State change tracking
        self._state_change_unsub: Callable[[], None] | None = None

    def _extract_entity_ids(self, value: Any) -> list[str]:
        """Extract entity IDs from a config value."""
        if isinstance(value, str) and "." in value:
            # Single entity ID
            return [value]
        elif isinstance(value, list):
            # List of entity IDs or mixed values
            return [v for v in value if isinstance(v, str) and "." in v]
        elif isinstance(value, dict):
            # Mapping (e.g., for forecast sensors)
            result = []
            for v in value.values():
                if isinstance(v, str) and "." in v:
                    result.append(v)
                elif isinstance(v, list):
                    result.extend(v2 for v2 in v if isinstance(v2, str) and "." in v2)
            return result
        return []

    async def async_setup(self) -> None:
        """Set up state change tracking."""
        if self._source_entity_ids:
            self._state_change_unsub = async_track_state_change_event(
                self.hass,
                list(self._source_entity_ids),
                self._handle_state_change,
            )

    async def async_shutdown(self) -> None:
        """Clean up state change tracking."""
        if self._state_change_unsub:
            self._state_change_unsub()
            self._state_change_unsub = None

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle source entity state change."""
        # Trigger refresh to reload values
        self.hass.async_create_task(self.async_request_refresh())

    async def _async_update_data(self) -> ElementInputData:
        """Load current values from source entities."""
        # Get forecast times from hub config
        hub_data = self._config_entry.data
        horizon_hours = hub_data.get(CONF_HORIZON_HOURS, DEFAULT_HORIZON_HOURS)
        period_minutes = hub_data.get(CONF_PERIOD_MINUTES, DEFAULT_PERIOD_MINUTES)

        # Calculate forecast timestamps
        now = dt_util.utcnow()
        forecast_timestamps = calculate_forecast_times(now, horizon_hours, period_minutes)

        # Load values for each field
        field_values: dict[str, list[float] | float | bool] = {}

        for field_name, value in self._subentry.data.items():
            if field_name in (CONF_NAME, CONF_ELEMENT_TYPE, CONF_CONNECTION):
                continue  # Skip non-input fields

            if field_name in self._field_sources:
                # Load from source entities
                loaded = await self._load_field_values(
                    field_name,
                    self._field_sources[field_name],
                    forecast_timestamps,
                )
                if loaded is not None:
                    field_values[field_name] = loaded
            else:
                # Static value from config
                if isinstance(value, bool):
                    field_values[field_name] = value
                elif isinstance(value, (int, float)):
                    field_values[field_name] = float(value)
                elif isinstance(value, list):
                    field_values[field_name] = [float(v) for v in value]

        # Notify network coordinator
        self._on_input_change()

        return ElementInputData(
            field_values=field_values,
            forecast_timestamps=forecast_timestamps,
        )

    async def _load_field_values(
        self,
        field_name: str,
        entity_ids: list[str],
        forecast_timestamps: tuple[float, ...],
    ) -> list[float] | None:
        """Load values from source entities with interpolation."""
        # Use existing TimeSeriesLoader
        loader = TimeSeriesLoader()
        try:
            return await loader.load(
                hass=self.hass,
                value=entity_ids,
                forecast_times=forecast_timestamps,
            )
        except Exception:
            _LOGGER.exception("Failed to load field %s from %s", field_name, entity_ids)
            return None

    def get_field_value(self, field_name: str) -> Any:
        """Get current value for a field (for input entities)."""
        if self.data is None:
            return None
        return self.data.field_values.get(field_name)
```

### 2. Update Runtime Data Structure (`__init__.py`)

```python
from dataclasses import dataclass


@dataclass(slots=True)
class HaeoRuntimeData:
    """Runtime data for HAEO integration."""

    network_coordinator: HaeoDataUpdateCoordinator
    element_coordinators: dict[str, ElementInputCoordinator]  # keyed by subentry_id


type HaeoConfigEntry = ConfigEntry[HaeoRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> bool:
    """Set up HAEO from a config entry."""

    # Callback for element coordinators to notify network coordinator
    def on_input_change() -> None:
        if entry.runtime_data and entry.runtime_data.network_coordinator:
            hass.async_create_task(entry.runtime_data.network_coordinator.async_request_refresh())

    # Create element coordinators for each subentry
    element_coordinators: dict[str, ElementInputCoordinator] = {}
    for subentry in entry.subentries.values():
        if subentry.subentry_type in ELEMENT_TYPES:
            coord = ElementInputCoordinator(hass, entry, subentry, on_input_change)
            await coord.async_setup()
            element_coordinators[subentry.subentry_id] = coord

    # Initialize element coordinators in parallel
    await asyncio.gather(*(coord.async_config_entry_first_refresh() for coord in element_coordinators.values()))

    # Create network coordinator (still uses old loading for now)
    network_coordinator = HaeoDataUpdateCoordinator(hass, entry)

    entry.runtime_data = HaeoRuntimeData(
        network_coordinator=network_coordinator,
        element_coordinators=element_coordinators,
    )

    # Initial network refresh
    await network_coordinator.async_config_entry_first_refresh()

    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: HaeoConfigEntry) -> bool:
    """Unload HAEO config entry."""
    # Clean up element coordinators
    if entry.runtime_data:
        for coord in entry.runtime_data.element_coordinators.values():
            await coord.async_shutdown()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

### 3. Update Input Entities to Use ElementInputCoordinator

Modify `HaeoInputNumber._handle_coordinator_update()`:

```python
def _handle_coordinator_update(self) -> None:
    """Handle coordinator data update."""
    if self._entity_mode == ConfigEntityMode.DRIVEN:
        # Get value from coordinator
        if self.coordinator.data:
            values = self.coordinator.data.field_values.get(self._field_info.field_name)
            if values is not None:
                if isinstance(values, list) and values:
                    self._attr_native_value = values[0]  # Current value is first
                    # Build forecast
                    self._attr_extra_state_attributes["forecast"] = [
                        {"time": ts, "value": v}
                        for ts, v in zip(
                            self.coordinator.data.forecast_timestamps,
                            values,
                            strict=False,
                        )
                    ]
                elif isinstance(values, (int, float)):
                    self._attr_native_value = float(values)

    self.async_write_ha_state()
```

## Testing Considerations

- Test source entity tracking triggers coordinator refresh
- Test parallel initialization of multiple element coordinators
- Test cleanup on subentry removal
- Test notification to network coordinator

## Acceptance Criteria

1. ElementInputCoordinator created per element subentry
2. Source entity state changes trigger coordinator refresh
3. Values loaded and interpolated correctly
4. Input entities update from coordinator data
5. Network coordinator notified when inputs change
6. Proper cleanup on unload

## Notes for Future Phases

- Phase 3 will modify NetworkOptimizationCoordinator to read from input entities
- The `_load_field_values` method may be refactored in Phase 3
