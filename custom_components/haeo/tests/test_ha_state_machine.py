"""Tests for the Home Assistant-backed state machine adapter."""

from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant

from custom_components.haeo.ha_state_machine import HomeAssistantStateMachine


async def test_time_zone_is_home_assistant_time_zone(hass: HomeAssistant) -> None:
    """Naive times are read in Home Assistant's configured time zone, not the system's."""
    await hass.config.async_set_time_zone("Australia/Adelaide")

    assert HomeAssistantStateMachine(hass).time_zone == ZoneInfo("Australia/Adelaide")


async def test_get_returns_home_assistant_state(hass: HomeAssistant) -> None:
    """Entity states come from Home Assistant's state machine."""
    hass.states.async_set("sensor.x", "1.0")

    state = HomeAssistantStateMachine(hass).get("sensor.x")

    assert state is not None
    assert state.state == "1.0"
