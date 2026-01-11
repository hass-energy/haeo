"""Tests for stale device removal functionality.

Device identifiers follow this pattern (v0.1.0 compatible):
(DOMAIN, f"{entry_id}_{subentry_id}_{device_name}")
"""

from types import MappingProxyType

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoConfigEntry, async_remove_config_entry_device
from custom_components.haeo.const import DOMAIN


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> HaeoConfigEntry:
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


@pytest.fixture
def mock_device_registry(hass: HomeAssistant) -> dr.DeviceRegistry:
    """Get the device registry."""
    return dr.async_get(hass)


async def test_keep_device_for_existing_element(
    hass: HomeAssistant,
    mock_config_entry: HaeoConfigEntry,
    mock_device_registry: dr.DeviceRegistry,
) -> None:
    """Test that devices for existing elements are kept."""
    # Add a subentry
    subentry = ConfigSubentry(
        data=MappingProxyType({"name": "Battery", "element_type": "battery"}),
        subentry_type="battery",
        title="Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_config_entry, subentry)

    # Create a device using the v0.1.0 pattern: {entry_id}_{subentry_id}_{device_name}
    device = mock_device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, f"{mock_config_entry.entry_id}_{subentry.subentry_id}_battery")},
        name="Battery",
        manufacturer="HAEO",
        model="Battery",
    )

    # Device should be kept (element still exists)
    result = await async_remove_config_entry_device(
        hass,
        mock_config_entry,
        device,
    )

    assert not result, "Device should be kept for existing element"


async def test_keep_sub_device_for_existing_element(
    hass: HomeAssistant,
    mock_config_entry: HaeoConfigEntry,
    mock_device_registry: dr.DeviceRegistry,
) -> None:
    """Test that sub-devices for existing elements are kept."""
    # Add a battery subentry (batteries can have sub-devices like partitions)
    subentry = ConfigSubentry(
        data=MappingProxyType({"name": "Battery", "element_type": "battery"}),
        subentry_type="battery",
        title="Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_config_entry, subentry)

    # Create a sub-device using the subentry_id_device_name pattern
    device = mock_device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, f"{mock_config_entry.entry_id}_{subentry.subentry_id}_battery_device_normal")},
        name="Battery Normal Partition",
        manufacturer="HAEO",
        model="Battery Partition",
    )

    # Sub-device should be kept (parent element still exists)
    result = await async_remove_config_entry_device(
        hass,
        mock_config_entry,
        device,
    )

    assert not result, "Sub-device should be kept for existing element"


async def test_remove_device_for_deleted_element(
    hass: HomeAssistant,
    mock_config_entry: HaeoConfigEntry,
    mock_device_registry: dr.DeviceRegistry,
) -> None:
    """Test that devices for deleted elements are removed."""
    # Create a device with a non-existent subentry_id using v0.1.0 pattern
    device = mock_device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, f"{mock_config_entry.entry_id}_deleted_subentry_id_battery")},
        name="Deleted Battery",
        manufacturer="HAEO",
        model="Battery",
    )

    # Device should be removed (element doesn't exist)
    result = await async_remove_config_entry_device(
        hass,
        mock_config_entry,
        device,
    )

    assert result, "Device should be removed for non-existent element"


async def test_remove_sub_device_for_deleted_element(
    hass: HomeAssistant,
    mock_config_entry: HaeoConfigEntry,
    mock_device_registry: dr.DeviceRegistry,
) -> None:
    """Test that sub-devices for deleted elements are removed."""
    # Create a sub-device with a non-existent subentry_id
    device = mock_device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, f"{mock_config_entry.entry_id}_deleted_subentry_id_battery_device_normal")},
        name="Deleted Battery Partition",
        manufacturer="HAEO",
        model="Battery Partition",
    )

    # Sub-device should be removed (parent element doesn't exist)
    result = await async_remove_config_entry_device(
        hass,
        mock_config_entry,
        device,
    )

    assert result, "Sub-device should be removed for non-existent element"


async def test_keep_hub_device(
    hass: HomeAssistant,
    mock_config_entry: HaeoConfigEntry,
    mock_device_registry: dr.DeviceRegistry,
) -> None:
    """Test that the hub device itself is always kept."""
    # Create the hub device (no subentry suffix)
    device = mock_device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, mock_config_entry.entry_id)},
        name="HAEO Hub",
        manufacturer="HAEO",
        model="Hub",
    )

    # Hub device should always be kept
    result = await async_remove_config_entry_device(
        hass,
        mock_config_entry,
        device,
    )

    assert not result, "Hub device should always be kept"


async def test_multiple_elements_device_cleanup(
    hass: HomeAssistant,
    mock_config_entry: HaeoConfigEntry,
    mock_device_registry: dr.DeviceRegistry,
) -> None:
    """Test device cleanup with multiple elements."""
    # Add multiple subentries
    subentries: list[ConfigSubentry] = []
    elements = ["Battery1", "Battery2", "Grid"]
    for element_name in elements:
        element_type = "battery" if "Battery" in element_name else "grid"
        subentry = ConfigSubentry(
            data=MappingProxyType({"name": element_name, "element_type": element_type}),
            subentry_type=element_type,
            title=element_name,
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(mock_config_entry, subentry)
        subentries.append(subentry)

    # Create devices for existing and non-existing elements using v0.1.0 pattern
    existing_device = mock_device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, f"{mock_config_entry.entry_id}_{subentries[0].subentry_id}_battery")},
        name="Battery1",
    )

    deleted_device = mock_device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, f"{mock_config_entry.entry_id}_old_deleted_subentry_id_battery")},
        name="OldElement",
    )

    # Existing device should be kept
    assert not await async_remove_config_entry_device(hass, mock_config_entry, existing_device)

    # Deleted device should be removed
    assert await async_remove_config_entry_device(hass, mock_config_entry, deleted_device)


async def test_device_with_wrong_domain(
    hass: HomeAssistant,
    mock_config_entry: HaeoConfigEntry,
    mock_device_registry: dr.DeviceRegistry,
) -> None:
    """Test that devices from other domains are handled correctly."""
    # Create a device with a different domain identifier
    device = mock_device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={("other_domain", "some_id")},
        name="Other Domain Device",
    )

    # Device with different domain should be kept (not managed by HAEO)
    result = await async_remove_config_entry_device(
        hass,
        mock_config_entry,
        device,
    )

    assert not result, "Device from other domain should be kept"
