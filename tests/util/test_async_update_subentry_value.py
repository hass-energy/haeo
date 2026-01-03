"""Tests for async_update_subentry_value utility function."""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any
from unittest.mock import Mock, patch

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_ELEMENT_TYPE,
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.util import async_update_subentry_value


@dataclass
class MockRuntimeData:
    """Mock runtime data for testing."""

    input_entities: dict[tuple[str, str], Any] = field(default_factory=dict)
    value_update_in_progress: bool = False


async def test_async_update_subentry_value_sets_flag(hass: HomeAssistant) -> None:
    """async_update_subentry_value sets value_update_in_progress flag."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    # Add a subentry
    subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: "node", CONF_NAME: "Test Node"}),
        subentry_type="node",
        title="Test Node",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, subentry)

    # Set up runtime data
    runtime_data = MockRuntimeData()
    entry.runtime_data = runtime_data

    # Mock async_update_subentry to capture the call
    with patch.object(hass.config_entries, "async_update_subentry") as mock_update:
        await async_update_subentry_value(hass, entry, subentry, "test_field", 42.0)

        # Verify the update was called with correct data
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs["data"]["test_field"] == 42.0

    # Verify flag is cleared after update
    assert runtime_data.value_update_in_progress is False


async def test_async_update_subentry_value_clears_flag_on_error(hass: HomeAssistant) -> None:
    """async_update_subentry_value clears flag even if update raises."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    # Add a subentry
    subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: "node", CONF_NAME: "Test Node"}),
        subentry_type="node",
        title="Test Node",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, subentry)

    # Set up runtime data
    runtime_data = MockRuntimeData()
    entry.runtime_data = runtime_data

    # Mock async_update_subentry to raise an exception
    with patch.object(hass.config_entries, "async_update_subentry", side_effect=RuntimeError("Test error")):
        try:
            await async_update_subentry_value(hass, entry, subentry, "test_field", 42.0)
        except RuntimeError:
            pass

    # Verify flag is cleared even after error
    assert runtime_data.value_update_in_progress is False


async def test_async_update_subentry_value_without_runtime_data(hass: HomeAssistant) -> None:
    """async_update_subentry_value works when runtime_data is None."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    # Add a subentry
    subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: "node", CONF_NAME: "Test Node"}),
        subentry_type="node",
        title="Test Node",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, subentry)

    # No runtime_data
    entry.runtime_data = None

    # Mock async_update_subentry
    with patch.object(hass.config_entries, "async_update_subentry") as mock_update:
        await async_update_subentry_value(hass, entry, subentry, "test_field", 42.0)

        # Verify the update was still called
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs["data"]["test_field"] == 42.0
