# Phase 1: Create Input Entity Infrastructure

## Goal

Create input entities (NumberEntity/SwitchEntity) from element configuration fields. These entities will be user-editable or driven by external sensors depending on the configuration value.

## Prerequisites

- None (first phase)

## Deliverables

1. `schema/input_fields.py` - Metadata defining which config fields become input entities
2. `entities/haeo_number.py` - HaeoInputNumber class
3. `entities/haeo_switch.py` - HaeoInputSwitch class
4. `number.py` - NUMBER platform setup
5. `switch.py` - SWITCH platform setup
6. Updated `__init__.py` - Register NUMBER and SWITCH platforms

## Implementation Details

### 1. Input Field Metadata (`schema/input_fields.py`)

Define which ConfigSchema fields should become input entities:

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any

from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass


class InputEntityType(Enum):
    """Type of input entity to create."""

    NUMBER = "number"
    SWITCH = "switch"


@dataclass(frozen=True, slots=True)
class InputFieldInfo:
    """Metadata for a config field that becomes an input entity."""

    field_name: str
    entity_type: InputEntityType
    output_type: str  # From model.const OUTPUT_TYPE_*
    unit: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    device_class: NumberDeviceClass | SensorDeviceClass | None = None
    translation_key: str | None = None
    direction: str | None = None  # "+" or "-" for power direction


def get_input_fields(element_type: str) -> list[InputFieldInfo]:
    """Return input field definitions for an element type."""
    # Implementation returns list of InputFieldInfo for each element
```

Key fields to expose as input entities:

- Battery: capacity, initial_charge_percentage, min_charge_percentage, max_charge_percentage, efficiency
- Grid: import_price, export_price, import_limit, export_limit
- Solar: forecast, price_production, curtailment (switch)
- Load: forecast
- Inverter: max_power_dc_to_ac, max_power_ac_to_dc, efficiency_dc_to_ac, efficiency_ac_to_dc
- Connection: max_power_source_target, max_power_target_source, price_source_target, price_target_source

### 2. HaeoInputNumber (`entities/haeo_number.py`)

```python
class ConfigEntityMode(Enum):
    """Operating mode for config entities."""

    EDITABLE = "editable"  # User can set value, no external source
    DRIVEN = "driven"  # Value driven by external entity


class HaeoInputNumber(RestoreNumber):
    """Number entity representing a configurable input parameter."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: Any,  # ElementInputCoordinator (Phase 2) or dummy for now
        config_entry: ConfigEntry,
        subentry: ConfigSubentry,
        field_info: InputFieldInfo,
        device_entry: DeviceEntry,
    ) -> None:
        self._config_entry = config_entry
        self._subentry = subentry
        self._field_info = field_info
        self._device_entry = device_entry

        # Determine mode from config value
        config_value = subentry.data.get(field_info.field_name)
        if isinstance(config_value, str) and config_value.startswith(("sensor.", "number.", "input_number.")):
            self._entity_mode = ConfigEntityMode.DRIVEN
            self._source_entity_ids = [config_value]  # Could be list for multi-sensor
        else:
            self._entity_mode = ConfigEntityMode.EDITABLE
            self._source_entity_ids = []

        # Unique ID for multi-hub safety
        self._attr_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{field_info.field_name}"

        # Entity attributes
        self._attr_has_entity_name = True
        self._attr_translation_key = field_info.translation_key or field_info.field_name
        self._attr_native_unit_of_measurement = field_info.unit
        self._attr_device_class = field_info.device_class
        self._attr_native_min_value = field_info.min_value
        self._attr_native_max_value = field_info.max_value
        self._attr_native_step = field_info.step
        self._attr_entity_category = EntityCategory.CONFIG

        # Initial value (for editable mode)
        if self._entity_mode == ConfigEntityMode.EDITABLE:
            self._attr_native_value = float(config_value) if config_value is not None else None
        else:
            self._attr_native_value = None  # Will be set by coordinator update

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(identifiers=self._device_entry.identifiers)

    async def async_added_to_hass(self) -> None:
        """Restore state on startup."""
        await super().async_added_to_hass()

        if self._entity_mode == ConfigEntityMode.EDITABLE:
            # Restore previous value if available
            if (last_data := await self.async_get_last_number_data()) and last_data.native_value is not None:
                self._attr_native_value = last_data.native_value

    async def async_set_native_value(self, value: float) -> None:
        """Handle user setting a value."""
        if self._entity_mode == ConfigEntityMode.DRIVEN:
            # In driven mode, user changes are ignored (read-only)
            self.async_write_ha_state()
            return

        self._attr_native_value = value
        self.async_write_ha_state()
        # Notify coordinator to trigger optimization refresh
        await self.coordinator.async_request_refresh()

    def get_current_value(self) -> float | None:
        """Return current value for optimization."""
        return self._attr_native_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = {
            "config_mode": self._entity_mode.value,
            "element_name": self._subentry.title,
            "element_type": self._subentry.subentry_type,
            "output_name": self._field_info.field_name,
            "output_type": self._field_info.output_type,
        }
        if self._source_entity_ids:
            attrs["source_entities"] = self._source_entity_ids
        if self._field_info.direction:
            attrs["direction"] = self._field_info.direction
        return attrs
```

### 3. HaeoInputSwitch (`entities/haeo_switch.py`)

Similar structure to HaeoInputNumber but for boolean fields:

```python
class HaeoInputSwitch(RestoreEntity, SwitchEntity):
    """Switch entity representing a configurable boolean parameter."""

    # Similar init pattern
    # async_turn_on / async_turn_off instead of async_set_native_value
    # get_current_value returns bool
```

### 4. Platform Setup (`number.py`, `switch.py`)

```python
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAEO number entities."""
    # Get coordinator (or dummy for Phase 1)
    coordinator = config_entry.runtime_data

    entities: list[HaeoInputNumber] = []
    dr = device_registry.async_get(hass)

    for subentry in config_entry.subentries.values():
        if subentry.subentry_type not in ELEMENT_TYPES:
            continue

        # Get input field definitions for this element type
        input_fields = get_input_fields(subentry.subentry_type)

        # Get or create device for this subentry
        device_entry = dr.async_get_or_create(
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{subentry.subentry_id}")},
            config_entry_id=config_entry.entry_id,
            config_subentry_id=subentry.subentry_id,
            translation_key=subentry.subentry_type,
            translation_placeholders={"name": subentry.title},
        )

        for field_info in input_fields:
            if field_info.field_name not in subentry.data:
                continue  # Optional field not configured

            entities.append(
                HaeoInputNumber(
                    hass=hass,
                    coordinator=coordinator,
                    config_entry=config_entry,
                    subentry=subentry,
                    field_info=field_info,
                    device_entry=device_entry,
                )
            )

    # Associate entities with their subentries
    for subentry in config_entry.subentries.values():
        subentry_entities = [e for e in entities if e._subentry.subentry_id == subentry.subentry_id]
        if subentry_entities:
            async_add_entities(subentry_entities, config_subentry_id=subentry.subentry_id)
```

### 5. Update `__init__.py`

```python
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER, Platform.SWITCH]
```

## Testing Considerations

- Test editable mode: user can set value, value persists across restart
- Test driven mode: entity is read-only, tracks external entity
- Test multi-hub: unique IDs don't conflict between hubs
- Test subentry removal: entities are cleaned up

## Acceptance Criteria

1. Number entities created for numeric config fields
2. Switch entities created for boolean config fields
3. Editable mode works for static config values
4. Driven mode works for entity ID config values
5. Entities associated with correct devices and subentries
6. Entities restore state after HA restart
7. Translations work for all input entities

## Notes for Future Phases

- Phase 2 will add ElementInputCoordinator that updates driven entities
- Phase 3 will make NetworkOptimizationCoordinator read from these entities
- Coordinator passed to entities will be ElementInputCoordinator, not network coordinator
