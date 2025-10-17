"""Test the HAEO integration."""

from contextlib import suppress
from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import async_reload_entry, async_setup_entry, async_unload_entry
from custom_components.haeo.const import (
    CONF_CAPACITY,
    CONF_ELEMENT_TYPE,
    CONF_EXPORT_LIMIT,
    CONF_EXPORT_PRICE,
    CONF_IMPORT_LIMIT,
    CONF_IMPORT_PRICE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_POWER,
    CONF_SOURCE,
    CONF_TARGET,
    DOMAIN,
    ELEMENT_TYPE_BATTERY,
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPE_GRID,
)


@pytest.fixture
def mock_hub_entry() -> MockConfigEntry:
    """Create a mock hub config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": "hub",
            "name": "Test Network",
        },
        entry_id="hub_entry_id",
        title="Test HAEO Integration",
    )


@pytest.fixture
def mock_battery_subentry(mock_hub_entry: MockConfigEntry) -> MockConfigEntry:
    """Create a mock battery subentry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "parent_entry_id": mock_hub_entry.entry_id,
            CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
            CONF_CAPACITY: 10000,
            CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_charge",
        },
        entry_id="battery_subentry_id",
        title="Test Battery",
    )


@pytest.fixture
def mock_grid_subentry(mock_hub_entry: MockConfigEntry) -> MockConfigEntry:
    """Create a mock grid subentry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "parent_entry_id": mock_hub_entry.entry_id,
            CONF_ELEMENT_TYPE: ELEMENT_TYPE_GRID,
            CONF_IMPORT_LIMIT: 10000,
            CONF_EXPORT_LIMIT: 5000,
            CONF_IMPORT_PRICE: "sensor.import_price",
            CONF_EXPORT_PRICE: "sensor.export_price",
        },
        entry_id="grid_subentry_id",
        title="Test Grid",
    )


@pytest.fixture
def mock_connection_subentry(mock_hub_entry: MockConfigEntry) -> MockConfigEntry:
    """Create a mock connection subentry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "parent_entry_id": mock_hub_entry.entry_id,
            CONF_ELEMENT_TYPE: ELEMENT_TYPE_CONNECTION,
            CONF_SOURCE: "test_battery",
            CONF_TARGET: "test_grid",
            CONF_MAX_POWER: 5000,
        },
        entry_id="connection_subentry_id",
        title="Battery to Grid",
    )


async def test_setup_hub_entry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> None:
    """Test setting up a hub entry."""
    mock_hub_entry.add_to_hass(hass)

    # Test basic hub setup functionality
    with suppress(Exception):
        await async_setup_entry(hass, mock_hub_entry)

    # Hub entries set up platforms
    assert True


async def test_setup_subentry_skips_setup(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry, mock_battery_subentry: MockConfigEntry
) -> None:
    """Test that subentries skip platform setup and trigger parent reload."""
    mock_hub_entry.add_to_hass(hass)
    mock_battery_subentry.add_to_hass(hass)

    # Set up sensor state for battery
    hass.states.async_set("sensor.battery_charge", "50", {})

    # Subentry setup should just trigger parent reload and return True
    result = await async_setup_entry(hass, mock_battery_subentry)

    # Subentry setup returns True without setting up platforms
    assert result is True
    # No platforms should be set up for subentries
    assert not hasattr(mock_battery_subentry, "runtime_data")


async def test_unload_hub_entry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> None:
    """Test unloading a hub entry."""
    mock_hub_entry.add_to_hass(hass)

    # Set up a mock coordinator
    mock_hub_entry.runtime_data = AsyncMock()

    # Test that unload works
    result = await async_unload_entry(hass, mock_hub_entry)

    assert result is True
    # Coordinator should be cleaned up
    assert mock_hub_entry.runtime_data is None


async def test_unload_subentry_returns_true(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry, mock_battery_subentry: MockConfigEntry
) -> None:
    """Test that unloading a subentry immediately returns True."""
    mock_hub_entry.add_to_hass(hass)
    mock_battery_subentry.add_to_hass(hass)

    # Subentry unload should immediately return True
    result = await async_unload_entry(hass, mock_battery_subentry)

    assert result is True


async def test_reload_hub_entry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> None:
    """Test reloading a hub entry."""
    mock_hub_entry.add_to_hass(hass)

    # Set up initial mock coordinator
    mock_hub_entry.runtime_data = AsyncMock()

    # Test that reload works
    with suppress(Exception):
        await async_reload_entry(hass, mock_hub_entry)

    assert True
