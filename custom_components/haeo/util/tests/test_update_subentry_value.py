"""Tests for async_update_subentry_value."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.util import async_update_subentry_value


@pytest.fixture
def mock_runtime_data() -> Mock:
    """Create mock runtime data with value_update_in_progress flag."""
    runtime_data = Mock()
    runtime_data.value_update_in_progress = False
    return runtime_data


async def test_flag_remains_set_after_call(
    hass: HomeAssistant,
    mock_runtime_data: Mock,
) -> None:
    """Flag stays True after async_update_subentry_value returns.

    The update listener (not this function) is responsible for clearing it.
    """
    entry = Mock()
    entry.runtime_data = mock_runtime_data

    subentry = ConfigSubentry(
        data=MappingProxyType({"power_limit": 5.0}),
        subentry_type="battery",
        title="Test Battery",
        subentry_id="test_id",
        unique_id=None,
    )

    hass.config_entries.async_update_subentry = Mock()

    await async_update_subentry_value(
        hass=hass,
        entry=entry,
        subentry=subentry,
        field_path=("power_limit",),
        value=10.0,
    )

    assert mock_runtime_data.value_update_in_progress is True
