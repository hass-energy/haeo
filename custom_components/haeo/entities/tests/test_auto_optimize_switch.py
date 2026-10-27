"""Tests for the auto-optimize switch entity."""

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.device_registry import DeviceEntry
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.entities.auto_optimize_switch import AutoOptimizeSwitch
from custom_components.haeo.entities.tests.entity_helpers import mock_state_writes


def _create_switch(hass: HomeAssistant) -> AutoOptimizeSwitch:
    """Create an auto-optimize switch for a config entry added to hass."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
    entry.add_to_hass(hass)
    return AutoOptimizeSwitch(
        config_entry=entry, device_entry=DeviceEntry(id="test_device_id", config_entry_id=entry.entry_id)
    )


@pytest.mark.parametrize(
    ("initial_state", "method", "expected"),
    [
        pytest.param(False, "on", True, id="turn_on"),
        pytest.param(True, "off", False, id="turn_off"),
    ],
)
async def test_auto_optimize_switch_toggle(
    hass: HomeAssistant,
    initial_state: bool,
    method: str,
    expected: bool,
) -> None:
    """Turning the auto-optimize switch updates state."""
    switch = _create_switch(hass)
    switch._attr_is_on = initial_state
    write_state = mock_state_writes(switch)

    if method == "on":
        await switch.async_turn_on()
    else:
        await switch.async_turn_off()

    assert switch.is_on is expected
    write_state.assert_called_once()


@pytest.mark.parametrize(
    ("restored_state", "expected"),
    [
        pytest.param(STATE_ON, True, id="restores_on"),
        pytest.param(STATE_OFF, False, id="restores_off"),
        pytest.param(None, True, id="defaults_on_without_previous_state"),
    ],
)
async def test_auto_optimize_switch_restores_state(
    hass: HomeAssistant,
    restored_state: str | None,
    expected: bool,
) -> None:
    """The switch restores its state from the previous session, and is on when there is none."""
    switch = _create_switch(hass)

    async def mock_get_last_state() -> State | None:
        return None if restored_state is None else State("switch.test", restored_state)

    switch.async_get_last_state = mock_get_last_state  # type: ignore[method-assign]

    await switch.async_added_to_hass()

    assert switch.is_on is expected
