"""Tests for the input store builder and subentry storage binding."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.data.input_store import InputMode
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements.grid import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.core.schema.elements.grid import ELEMENT_TYPE as GRID_TYPE
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON, HUB_SECTION_TIERS
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.input_stores import SubentryStorage, build_input_stores


@pytest.fixture
def horizon_manager() -> Mock:
    """Return a mock horizon manager."""
    manager = Mock(spec=HorizonManager)
    manager.get_forecast_timestamps.return_value = (0.0, 300.0, 600.0)
    manager.subscribe.return_value = Mock()
    return manager


@pytest.fixture
def config_entry(hass: HomeAssistant, horizon_manager: Mock) -> MockConfigEntry:
    """Return a config entry with runtime data for store tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Network",
        data={
            HUB_SECTION_COMMON: {CONF_NAME: "Test Network"},
            HUB_SECTION_TIERS: {
                "tier_1_count": 2,
                "tier_1_duration": 5,
                "tier_2_count": 0,
                "tier_2_duration": 15,
                "tier_3_count": 0,
                "tier_3_duration": 30,
                "tier_4_count": 0,
                "tier_4_duration": 60,
            },
            HUB_SECTION_ADVANCED: {},
        },
        entry_id="test_input_stores_entry",
    )
    entry.add_to_hass(hass)
    entry.runtime_data = HaeoRuntimeData(coordinator=None, horizon_manager=horizon_manager)
    return entry


def _add_grid(hass: HomeAssistant, entry: MockConfigEntry) -> ConfigSubentry:
    """Add a grid subentry with one constant field, one driven field, one none field."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: GRID_TYPE,
                CONF_NAME: "Main Grid",
                CONF_CONNECTION: as_connection_target("main_bus"),
                SECTION_PRICING: {
                    CONF_PRICE_SOURCE_TARGET: as_constant_value(0.30),
                    CONF_PRICE_TARGET_SOURCE: as_entity_value(["sensor.export_price"]),
                },
                SECTION_POWER_LIMITS: {
                    CONF_MAX_POWER_SOURCE_TARGET: as_none_value(),
                    CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
                },
            }
        ),
        subentry_type=GRID_TYPE,
        title="Main Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, subentry)
    return subentry


def test_build_input_stores_creates_stores_for_configured_fields(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    horizon_manager: Mock,
) -> None:
    """build_input_stores creates a store per configured field and skips none fields."""
    _add_grid(hass, config_entry)

    stores = build_input_stores(hass, config_entry, horizon_manager)

    constant_key = ("Main Grid", (SECTION_PRICING, CONF_PRICE_SOURCE_TARGET))
    driven_key = ("Main Grid", (SECTION_PRICING, CONF_PRICE_TARGET_SOURCE))
    limit_key = ("Main Grid", (SECTION_POWER_LIMITS, CONF_MAX_POWER_TARGET_SOURCE))
    none_key = ("Main Grid", (SECTION_POWER_LIMITS, CONF_MAX_POWER_SOURCE_TARGET))

    assert constant_key in stores
    assert driven_key in stores
    assert limit_key in stores
    # None/disabled field gets no store
    assert none_key not in stores

    assert stores[constant_key].mode == InputMode.EDITABLE
    assert stores[driven_key].mode == InputMode.DRIVEN
    assert stores[driven_key].source_entity_ids == ["sensor.export_price"]


def test_subentry_storage_read_returns_persisted_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """SubentryStorage.read returns the live persisted schema value."""
    subentry = _add_grid(hass, config_entry)
    storage = SubentryStorage(
        hass,
        config_entry,
        subentry.subentry_id,
        (SECTION_PRICING, CONF_PRICE_SOURCE_TARGET),
    )

    assert storage.read() == as_constant_value(0.30)


async def test_subentry_storage_write_updates_subentry(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """SubentryStorage.write persists a new value to the subentry."""
    subentry = _add_grid(hass, config_entry)
    storage = SubentryStorage(
        hass,
        config_entry,
        subentry.subentry_id,
        (SECTION_PRICING, CONF_PRICE_SOURCE_TARGET),
    )

    await storage.write(as_constant_value(0.45))

    # Read back through a fresh lookup to confirm the live subentry changed
    assert storage.read() == as_constant_value(0.45)
    assert config_entry.runtime_data.value_update_in_progress is True
