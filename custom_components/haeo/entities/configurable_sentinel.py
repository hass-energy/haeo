"""Configurable sentinel entity for config flow value entry.

This sensor entity appears in EntitySelector dropdowns to let users indicate
they want to enter a constant value instead of selecting an external entity.
"""

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory

from custom_components.haeo.const import HAEO_CONFIGURABLE_UNIQUE_ID


class HaeoConfigurableSentinel(SensorEntity):
    """Sentinel entity for config flow configurable fields.

    This sensor serves as a marker in EntitySelector dropdowns. When selected,
    the config flow shows a number/text input for the user to enter a constant
    value instead of linking to an external sensor.

    The entity has a static state and never changes. It's created once during
    the first config entry setup and persists across all HAEO configurations.
    """

    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_name = "HAEO Configurable"
    _attr_icon = "mdi:tune"
    _attr_unique_id = HAEO_CONFIGURABLE_UNIQUE_ID
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_value = "configurable"
    _attr_available = True


__all__ = ["HaeoConfigurableSentinel"]
