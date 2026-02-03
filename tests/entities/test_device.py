"""Tests for centralized device creation in entities/device.py."""

from types import MappingProxyType

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN, ELEMENT_TYPE_NETWORK
from custom_components.haeo.entities.device import (
    build_device_identifier,
    get_or_create_element_device,
    get_or_create_network_device,
)


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test HAEO",
        data={},
        entry_id="test_entry_123",
        unique_id="test_unique_id",
    )
    entry.add_to_hass(hass)
    return entry


class TestGetOrCreateElementDevice:
    """Tests for get_or_create_element_device function."""

    async def test_main_device_identifier_pattern(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test main device uses {entry_id}_{subentry_id}_{device_name} identifier pattern."""
        subentry = ConfigSubentry(
            data=MappingProxyType({"name": "My Battery", "element_type": "battery"}),
            subentry_type="battery",
            title="My Battery",
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(mock_config_entry, subentry)

        # Create main device (device_name == element_type)
        device = get_or_create_element_device(hass, mock_config_entry, subentry, "battery")

        expected_identifier = (DOMAIN, f"{mock_config_entry.entry_id}_{subentry.subentry_id}_battery")
        assert expected_identifier in device.identifiers

    async def test_same_device_returned_on_subsequent_calls(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test that calling get_or_create_element_device twice returns the same device."""
        subentry = ConfigSubentry(
            data=MappingProxyType({"name": "Battery", "element_type": "battery"}),
            subentry_type="battery",
            title="Battery",
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(mock_config_entry, subentry)

        device1 = get_or_create_element_device(hass, mock_config_entry, subentry, "battery")
        device2 = get_or_create_element_device(hass, mock_config_entry, subentry, "battery")

        assert device1.id == device2.id


class TestGetOrCreateNetworkDevice:
    """Tests for get_or_create_network_device function."""

    async def test_network_device_identifier_pattern(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test network device uses {entry_id}_{subentry_id}_{network} identifier pattern."""
        network_subentry = ConfigSubentry(
            data=MappingProxyType({"name": "System", "element_type": ELEMENT_TYPE_NETWORK}),
            subentry_type=ELEMENT_TYPE_NETWORK,
            title="System",
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(mock_config_entry, network_subentry)

        device = get_or_create_network_device(hass, mock_config_entry, network_subentry)

        expected_identifier = (
            DOMAIN,
            f"{mock_config_entry.entry_id}_{network_subentry.subentry_id}_{ELEMENT_TYPE_NETWORK}",
        )
        assert expected_identifier in device.identifiers


class TestBuildDeviceIdentifier:
    """Tests for build_device_identifier function."""

    async def test_main_device_identifier(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test building identifier for main device."""
        subentry = ConfigSubentry(
            data=MappingProxyType({"name": "Battery", "element_type": "battery"}),
            subentry_type="battery",
            title="Battery",
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(mock_config_entry, subentry)

        identifier = build_device_identifier(mock_config_entry, subentry, "battery")

        expected = (DOMAIN, f"{mock_config_entry.entry_id}_{subentry.subentry_id}_battery")
        assert identifier == expected


class TestDeviceConsistency:
    """Tests ensuring consistent device identifiers across platforms."""

    async def test_input_and_output_use_same_device(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test that input entities (number/switch) and output sensors use the same device.

        This verifies that the centralized device creation fixes the previous
        bug where number.py/switch.py used a different identifier pattern than sensor.py.
        """
        subentry = ConfigSubentry(
            data=MappingProxyType({"name": "Grid", "element_type": "grid"}),
            subentry_type="grid",
            title="Grid",
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(mock_config_entry, subentry)

        # Simulate what number.py/switch.py does (main device)
        input_device = get_or_create_element_device(hass, mock_config_entry, subentry, "grid")

        # Simulate what sensor.py does (main device)
        output_device = get_or_create_element_device(hass, mock_config_entry, subentry, "grid")

        # They should be the exact same device
        assert input_device.id == output_device.id

    async def test_identifier_matches_built_identifier(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test that created device identifier matches build_device_identifier output."""
        subentry = ConfigSubentry(
            data=MappingProxyType({"name": "Battery", "element_type": "battery"}),
            subentry_type="battery",
            title="Battery",
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(mock_config_entry, subentry)

        device = get_or_create_element_device(hass, mock_config_entry, subentry, "battery")
        expected_identifier = build_device_identifier(mock_config_entry, subentry, "battery")

        assert expected_identifier in device.identifiers

    async def test_different_elements_get_different_devices(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test that different elements get different devices."""
        battery_subentry = ConfigSubentry(
            data=MappingProxyType({"name": "Battery", "element_type": "battery"}),
            subentry_type="battery",
            title="Battery",
            unique_id=None,
        )
        grid_subentry = ConfigSubentry(
            data=MappingProxyType({"name": "Grid", "element_type": "grid"}),
            subentry_type="grid",
            title="Grid",
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(mock_config_entry, battery_subentry)
        hass.config_entries.async_add_subentry(mock_config_entry, grid_subentry)

        battery_device = get_or_create_element_device(hass, mock_config_entry, battery_subentry, "battery")
        grid_device = get_or_create_element_device(hass, mock_config_entry, grid_subentry, "grid")

        assert battery_device.id != grid_device.id

    async def test_network_device_separate_from_element_devices(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test that network device is separate from element devices."""
        network_subentry = ConfigSubentry(
            data=MappingProxyType({"name": "System", "element_type": ELEMENT_TYPE_NETWORK}),
            subentry_type=ELEMENT_TYPE_NETWORK,
            title="System",
            unique_id=None,
        )
        battery_subentry = ConfigSubentry(
            data=MappingProxyType({"name": "Battery", "element_type": "battery"}),
            subentry_type="battery",
            title="Battery",
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(mock_config_entry, network_subentry)
        hass.config_entries.async_add_subentry(mock_config_entry, battery_subentry)

        network_device = get_or_create_network_device(hass, mock_config_entry, network_subentry)
        battery_device = get_or_create_element_device(hass, mock_config_entry, battery_subentry, "battery")

        assert network_device.id != battery_device.id
