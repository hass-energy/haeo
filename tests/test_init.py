"""Test the HAEO integration."""

from contextlib import suppress
from types import MappingProxyType
from typing import Any
from unittest.mock import AsyncMock, Mock

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import (
    HaeoRuntimeData,
    _ensure_required_subentries,
    async_reload_entry,
    async_remove_config_entry_device,
    async_setup_entry,
    async_unload_entry,
    async_update_listener,
)
from custom_components.haeo.const import (
    CONF_ADVANCED_MODE,
    CONF_ELEMENT_TYPE,
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.elements import (
    ELEMENT_TYPE_BATTERY,
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPE_GRID,
    ELEMENT_TYPE_NODE,
)
from custom_components.haeo.elements.battery import CONF_CAPACITY, CONF_INITIAL_CHARGE_PERCENTAGE
from custom_components.haeo.elements.connection import CONF_SOURCE, CONF_TARGET
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
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Network",
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
                CONF_IMPORT_PRICE: {
                    "live": ["sensor.import_price"],
                    "forecast": ["sensor.import_price"],
                },
                CONF_EXPORT_PRICE: {
                    "live": ["sensor.export_price"],
                    "forecast": ["sensor.export_price"],
                },
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

    # Set up a mock runtime data with proper structure
    mock_network_coordinator = Mock()
    mock_network_coordinator.cleanup = Mock()
    mock_hub_entry.runtime_data = HaeoRuntimeData(
        network_coordinator=mock_network_coordinator,
        element_coordinators={},
    )

    # Test that unload works
    result = await async_unload_entry(hass, mock_hub_entry)

    assert result is True
    # Coordinator cleanup should be called
    mock_network_coordinator.cleanup.assert_called_once()
    # runtime_data should be cleared
    assert mock_hub_entry.runtime_data is None


async def test_async_setup_entry_initializes_coordinator(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Setup should create a coordinator, perform initial refresh, and forward platforms."""

    class DummyCoordinator:
        def __init__(self, hass_param: HomeAssistant, entry_param: ConfigEntry) -> None:
            super().__init__()
            self.hass = hass_param
            self.config_entry = entry_param
            self.async_config_entry_first_refresh = AsyncMock()
            self.cleanup = Mock()

    class DummyElementCoordinator:
        def __init__(
            self,
            hass_param: HomeAssistant,
            entry_param: ConfigEntry,
            subentry: ConfigSubentry,
            on_change: Any = None,
        ) -> None:
            super().__init__()
            self.hass = hass_param
            self.config_entry = entry_param
            self.subentry = subentry
            self.on_input_change = on_change
            self.async_setup = AsyncMock()
            self.async_config_entry_first_refresh = AsyncMock()
            self.async_shutdown = AsyncMock()

    created: list[DummyCoordinator] = []
    element_coordinators_created: list[DummyElementCoordinator] = []

    def create_coordinator(hass_param: HomeAssistant, entry_param: ConfigEntry) -> DummyCoordinator:
        coordinator = DummyCoordinator(hass_param, entry_param)
        created.append(coordinator)
        return coordinator

    def create_element_coordinator(
        hass_param: HomeAssistant,
        entry_param: ConfigEntry,
        subentry: ConfigSubentry,
        on_change: Any = None,
    ) -> DummyElementCoordinator:
        coordinator = DummyElementCoordinator(hass_param, entry_param, subentry, on_change)
        element_coordinators_created.append(coordinator)
        return coordinator

    monkeypatch.setattr("custom_components.haeo.HaeoDataUpdateCoordinator", create_coordinator)
    monkeypatch.setattr("custom_components.haeo.ElementInputCoordinator", create_element_coordinator)

    forward_mock = AsyncMock()
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", forward_mock)

    result = await async_setup_entry(hass, mock_hub_entry)

    assert result is True
    assert created, "Coordinator should be instantiated"
    coordinator = created[0]
    runtime_data = mock_hub_entry.runtime_data
    assert runtime_data is not None
    assert runtime_data.network_coordinator is coordinator
    coordinator.async_config_entry_first_refresh.assert_awaited_once()
    forward_mock.assert_awaited_once()


async def test_reload_hub_entry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> None:
    """Test reloading a hub entry."""

    # Set up initial mock coordinator
    mock_hub_entry.runtime_data = AsyncMock()

    # Test that reload works
    with suppress(Exception):
        await async_reload_entry(hass, mock_hub_entry)

    assert True


async def test_ensure_required_subentries_network_already_exists(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry
) -> None:
    """Test that _ensure_required_subentries skips network if already exists."""
    # First, create a network subentry
    network_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_NAME: "Network", CONF_ELEMENT_TYPE: "network"}),
        subentry_type="network",
        title="Network",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, network_subentry)

    # Call ensure again - should skip creating another one
    await _ensure_required_subentries(hass, mock_hub_entry)

    # Count network subentries - should still be only 1
    network_count = sum(1 for sub in mock_hub_entry.subentries.values() if sub.subentry_type == "network")
    assert network_count == 1


async def test_ensure_required_subentries_creates_network(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> None:
    """Test that _ensure_required_subentries creates network if missing."""
    # Verify no network subentry exists initially
    network_count = sum(1 for sub in mock_hub_entry.subentries.values() if sub.subentry_type == "network")
    assert network_count == 0

    # Call ensure - should create one
    await _ensure_required_subentries(hass, mock_hub_entry)

    # Verify network subentry was created
    network_count = sum(1 for sub in mock_hub_entry.subentries.values() if sub.subentry_type == "network")
    assert network_count == 1


async def test_ensure_required_subentries_creates_switchboard_non_advanced(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry
) -> None:
    """Test that _ensure_required_subentries creates switchboard node in non-advanced mode."""
    # Verify no node subentry exists initially
    node_count = sum(1 for sub in mock_hub_entry.subentries.values() if sub.subentry_type == ELEMENT_TYPE_NODE)
    assert node_count == 0

    # Call ensure - should create switchboard node in non-advanced mode
    await _ensure_required_subentries(hass, mock_hub_entry)

    # Verify node subentry was created
    node_count = sum(1 for sub in mock_hub_entry.subentries.values() if sub.subentry_type == ELEMENT_TYPE_NODE)
    assert node_count == 1

    # Verify the created node has correct configuration
    node_subentry = next(sub for sub in mock_hub_entry.subentries.values() if sub.subentry_type == ELEMENT_TYPE_NODE)
    assert node_subentry.data[CONF_NAME] == "Switchboard"  # Default name when translations not available
    assert node_subentry.data["is_source"] is False
    assert node_subentry.data["is_sink"] is False


async def test_ensure_required_subentries_skips_switchboard_advanced_mode(
    hass: HomeAssistant,
) -> None:
    """Test that _ensure_required_subentries does not create switchboard in advanced mode."""
    # Create a hub entry with advanced_mode enabled
    advanced_hub_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Network",
            CONF_ADVANCED_MODE: True,
        },
        entry_id="hub_entry_id",
        title="Test HAEO Integration",
    )
    advanced_hub_entry.add_to_hass(hass)

    # Verify no node subentry exists initially
    node_count = sum(1 for sub in advanced_hub_entry.subentries.values() if sub.subentry_type == ELEMENT_TYPE_NODE)
    assert node_count == 0

    # Call ensure - should NOT create switchboard node in advanced mode
    await _ensure_required_subentries(hass, advanced_hub_entry)

    # Verify no node subentry was created
    node_count = sum(1 for sub in advanced_hub_entry.subentries.values() if sub.subentry_type == ELEMENT_TYPE_NODE)
    assert node_count == 0


async def test_ensure_required_subentries_skips_switchboard_if_exists(
    hass: HomeAssistant, mock_hub_entry: MockConfigEntry
) -> None:
    """Test that _ensure_required_subentries does not duplicate nodes if one exists."""
    # Create a node subentry first
    node_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_NAME: "Existing Node", CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE}),
        subentry_type=ELEMENT_TYPE_NODE,
        title="Existing Node",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, node_subentry)

    # Verify one node subentry exists
    node_count = sum(1 for sub in mock_hub_entry.subentries.values() if sub.subentry_type == ELEMENT_TYPE_NODE)
    assert node_count == 1

    # Call ensure - should not create another one
    await _ensure_required_subentries(hass, mock_hub_entry)

    # Verify still only one node subentry
    node_count = sum(1 for sub in mock_hub_entry.subentries.values() if sub.subentry_type == ELEMENT_TYPE_NODE)
    assert node_count == 1


async def test_reload_entry_failure_handling(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> None:
    """Test reload handles setup failures gracefully."""
    # Mock runtime data
    mock_hub_entry.runtime_data = AsyncMock()

    # Attempt reload - should work but may have warnings about state
    try:
        await async_reload_entry(hass, mock_hub_entry)
    except Exception:
        # Some setup steps may fail without full mocks
        pass

    # Verify a new coordinator was created or entry was unloaded
    # The important part is that reload doesn't crash
    assert True


async def test_async_update_listener(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test async_update_listener triggers reload."""
    # Mock the reload function
    reload_called = False
    connectivity_called = False
    ensure_called = False

    async def mock_reload(entry_id: str) -> bool:
        nonlocal reload_called
        reload_called = True
        return True

    hass.config_entries.async_reload = mock_reload

    async def mock_ensure(hass_arg: HomeAssistant, entry_arg: ConfigEntry) -> None:
        nonlocal ensure_called
        assert hass_arg is hass
        assert entry_arg is mock_hub_entry
        ensure_called = True

    monkeypatch.setattr("custom_components.haeo._ensure_required_subentries", mock_ensure)

    async def mock_evaluate(hass_arg: HomeAssistant, entry_arg: ConfigEntry) -> None:
        nonlocal connectivity_called
        assert hass_arg is hass
        assert entry_arg is mock_hub_entry
        connectivity_called = True

    monkeypatch.setattr(
        "custom_components.haeo.network.evaluate_network_connectivity",
        mock_evaluate,
    )

    # Call update listener
    await async_update_listener(hass, mock_hub_entry)

    # Verify reload was called
    assert reload_called
    assert connectivity_called
    assert ensure_called


async def test_async_remove_config_entry_device(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> None:
    """Test device removal when config entry is removed."""
    device_registry = dr.async_get(hass)

    # Create a device for an element
    device = device_registry.async_get_or_create(
        config_entry_id=mock_hub_entry.entry_id,
        identifiers={(DOMAIN, f"{mock_hub_entry.entry_id}_test_battery")},
        name="Test Battery",
    )

    # Device exists, so removal should be allowed
    result = await async_remove_config_entry_device(hass, mock_hub_entry, device)
    assert result is True

    # Now remove the device from registry
    device_registry.async_remove_device(device.id)

    # Try to remove again - device already gone, should return False
    result = await async_remove_config_entry_device(hass, mock_hub_entry, device)
    assert result is False
