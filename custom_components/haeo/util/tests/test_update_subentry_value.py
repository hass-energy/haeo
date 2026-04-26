"""Tests for async_update_subentry_value."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
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
    hass.config_entries.async_update_subentry.assert_called_once()
    call_args = hass.config_entries.async_update_subentry.call_args
    assert call_args is not None
    assert call_args.kwargs["data"]["power_limit"] == 10.0


async def test_flag_cleared_on_exception(
    hass: HomeAssistant,
    mock_runtime_data: Mock,
) -> None:
    """Flag is cleared if async_update_subentry raises an exception."""
    entry = Mock()
    entry.runtime_data = mock_runtime_data

    subentry = ConfigSubentry(
        data=MappingProxyType({"power_limit": 5.0}),
        subentry_type="battery",
        title="Test Battery",
        subentry_id="test_id",
        unique_id=None,
    )

    hass.config_entries.async_update_subentry = Mock(
        side_effect=RuntimeError("update failed"),
    )

    with pytest.raises(RuntimeError, match="update failed"):
        await async_update_subentry_value(
            hass=hass,
            entry=entry,
            subentry=subentry,
            field_path=("power_limit",),
            value=10.0,
        )

    assert mock_runtime_data.value_update_in_progress is False


async def test_nested_value_update_fires_listener(
    hass: HomeAssistant,
) -> None:
    """Updating a nested field actually triggers the HA update listener.

    A shallow copy of MappingProxyType shares nested containers, so
    mutating via set_nested_config_value_by_path would silently modify
    the original data.  async_update_subentry then sees no change and
    skips the listener.
    """
    # Only needed in this test, not the module
    from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: PLC0415

    from custom_components.haeo.const import DOMAIN  # noqa: PLC0415
    from custom_components.haeo.core.schema.constant_value import as_constant_value  # noqa: PLC0415

    entry = MockConfigEntry(domain=DOMAIN, entry_id="nested_test")
    entry.add_to_hass(hass)
    entry.runtime_data = Mock()
    entry.runtime_data.value_update_in_progress = False

    subentry = ConfigSubentry(
        data=MappingProxyType({
            "rules": [
                {"name": "r1", "price": as_constant_value(0.02)},
            ],
        }),
        subentry_type="policy",
        title="Policies",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, subentry)

    listener_called = False

    async def _listener(_hass: HomeAssistant, _entry: ConfigEntry) -> None:
        nonlocal listener_called
        listener_called = True

    entry.add_update_listener(_listener)

    await async_update_subentry_value(
        hass=hass,
        entry=entry,
        subentry=subentry,
        field_path=("rules", "0", "price"),
        value=as_constant_value(0.10),
    )
    await hass.async_block_till_done()

    assert listener_called, (
        "Update listener must fire when a nested field changes. "
        "A shallow copy of MappingProxyType shares nested containers, "
        "causing async_update_subentry to see no change."
    )
