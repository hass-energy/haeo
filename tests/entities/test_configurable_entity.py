"""Tests for the ConfigurableEntity."""

from custom_components.haeo.const import CONFIGURABLE_ENTITY_UNIQUE_ID
from custom_components.haeo.entities.configurable_entity import ConfigurableEntity


def test_configurable_entity_attributes() -> None:
    """Configurable entity has correct static attributes."""
    entity = ConfigurableEntity()

    assert entity.unique_id == CONFIGURABLE_ENTITY_UNIQUE_ID
    assert entity.name == "HAEO Configurable"
    assert entity.icon == "mdi:tune"
    assert entity.state == "configurable"
    assert entity.should_poll is False
