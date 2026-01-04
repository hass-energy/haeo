"""Configurable entity for config flow value entry.

This entity appears in EntitySelector dropdowns to let users indicate
they want to enter a constant value instead of selecting an external entity.
"""

from homeassistant.helpers.entity import Entity

from custom_components.haeo.const import CONFIGURABLE_ENTITY_UNIQUE_ID


class ConfigurableEntity(Entity):
    """Sentinel entity for config flow configurable fields.

    This entity serves as a marker in EntitySelector dropdowns. When selected,
    the config flow shows a number/text input for the user to enter a constant
    value instead of linking to an external sensor.

    The entity has a static state and never changes. It's created once during
    the first config entry setup and persists across all HAEO configurations.

    Registered under the haeo domain to give entity_id: haeo.configurable_entity
    """

    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_name = "HAEO Configurable"
    _attr_icon = "mdi:tune"
    _attr_unique_id = CONFIGURABLE_ENTITY_UNIQUE_ID
    _attr_state = "configurable"


__all__ = ["ConfigurableEntity"]
