"""Tests for the HaeoConfigurableSentinel entity."""

from custom_components.haeo.const import HAEO_CONFIGURABLE_UNIQUE_ID
from custom_components.haeo.entities.configurable_sentinel import HaeoConfigurableSentinel


def test_sentinel_attributes() -> None:
    """Sentinel entity has correct static attributes."""
    entity = HaeoConfigurableSentinel()

    assert entity.unique_id == HAEO_CONFIGURABLE_UNIQUE_ID
    assert entity.name == "HAEO Configurable"
    assert entity.icon == "mdi:tune"
    assert entity.native_value == "configurable"
    assert entity.should_poll is False
    assert entity.available is True
