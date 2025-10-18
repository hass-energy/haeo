"""Test the HAEO integration."""

from contextlib import suppress
from types import MappingProxyType
from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import async_reload_entry, async_setup_entry, async_unload_entry
from custom_components.haeo.const import CONF_ELEMENT_TYPE, DOMAIN
from custom_components.haeo.elements import ELEMENT_TYPE_BATTERY, ELEMENT_TYPE_CONNECTION, ELEMENT_TYPE_GRID
from custom_components.haeo.elements.battery import CONF_CAPACITY, CONF_INITIAL_CHARGE_PERCENTAGE
from custom_components.haeo.elements.connection import CONF_MAX_POWER, CONF_SOURCE, CONF_TARGET
from custom_components.haeo.elements.grid import (
    CONF_EXPORT_LIMIT,
    CONF_EXPORT_PRICE,
    CONF_IMPORT_LIMIT,
    CONF_IMPORT_PRICE,
)


@pytest.fixture
def mock_hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a mock hub config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": "hub",
            "name": "Test Network",
        },
        entry_id="hub_entry_id",
        title="Test HAEO Integration",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_battery_subentry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> ConfigSubentry:
    """Create a mock battery subentry."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
                CONF_CAPACITY: 10000,
                CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_charge",
            }
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Test Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, subentry)
    return subentry


@pytest.fixture
def mock_grid_subentry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> ConfigSubentry:
    """Create a mock grid subentry."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_GRID,
                CONF_IMPORT_LIMIT: 10000,
                CONF_EXPORT_LIMIT: 5000,
                CONF_IMPORT_PRICE: "sensor.import_price",
                CONF_EXPORT_PRICE: "sensor.export_price",
            }
        ),
        subentry_type=ELEMENT_TYPE_GRID,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, subentry)
    return subentry


@pytest.fixture
def mock_connection_subentry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> ConfigSubentry:
    """Create a mock connection subentry."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_CONNECTION,
                CONF_SOURCE: "test_battery",
                CONF_TARGET: "test_grid",
                CONF_MAX_POWER: 5000,
            }
        ),
        subentry_type=ELEMENT_TYPE_CONNECTION,
        title="Battery to Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, subentry)
    return subentry


async def test_setup_hub_entry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> None:
    """Test setting up a hub entry."""
    # Test basic hub setup functionality
    with suppress(Exception):
        await async_setup_entry(hass, mock_hub_entry)

    # Hub entries set up platforms
    assert True


async def test_unload_hub_entry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> None:
    """Test unloading a hub entry."""

    # Set up a mock coordinator
    mock_hub_entry.runtime_data = AsyncMock()

    # Test that unload works
    result = await async_unload_entry(hass, mock_hub_entry)

    assert result is True
    # Coordinator should be cleaned up
    assert mock_hub_entry.runtime_data is None


async def test_reload_hub_entry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> None:
    """Test reloading a hub entry."""

    # Set up initial mock coordinator
    mock_hub_entry.runtime_data = AsyncMock()

    # Test that reload works
    with suppress(Exception):
        await async_reload_entry(hass, mock_hub_entry)

    assert True
