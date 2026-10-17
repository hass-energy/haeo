"""Tests for EV adapter availability checks."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import ElementType, ev
from custom_components.haeo.elements.availability import schema_config_available


def _ev_schema(soc_entity: str, *, with_trip: bool = False) -> ev.EvConfigSchema:
    """Build an EV config schema pointing at the given SOC entity."""
    config: dict[str, object] = {
        "element_type": ElementType.EV,
        "name": "test_ev",
        "connection": as_connection_target("switchboard"),
        ev.SECTION_VEHICLE: {
            ev.CONF_CAPACITY: as_constant_value(60.0),
            ev.CONF_ENERGY_PER_DISTANCE: as_constant_value(0.15),
            ev.CONF_CURRENT_SOC: as_entity_value([soc_entity]),
        },
        ev.SECTION_CHARGING: {
            ev.CONF_MAX_CHARGE_RATE: as_constant_value(7.4),
        },
        "power_limits": {},
        "efficiency": {},
    }
    if with_trip:
        config[ev.SECTION_TRIP] = {
            ev.CONF_TRIP_CALENDAR: as_entity_value(["calendar.ev_trips"]),
        }
    return config  # type: ignore[return-value]  # constructed to match EvConfigSchema


async def test_available_returns_true_when_soc_sensor_exists(hass: HomeAssistant) -> None:
    """EV availability requires the SOC sensor to exist."""
    hass.states.async_set("sensor.ev_soc", "80.0", {"unit_of_measurement": "%"})

    assert schema_config_available(_ev_schema("sensor.ev_soc"), sm=hass.states) is True


async def test_available_returns_false_when_soc_sensor_missing(hass: HomeAssistant) -> None:
    """A missing SOC sensor makes the EV unavailable."""
    assert schema_config_available(_ev_schema("sensor.missing"), sm=hass.states) is False


async def test_trip_calendar_gates_availability_like_any_entity(hass: HomeAssistant) -> None:
    """The trip calendar is an entity like any other: the EV is available once it exists."""
    hass.states.async_set("sensor.ev_soc", "80.0", {"unit_of_measurement": "%"})
    assert schema_config_available(_ev_schema("sensor.ev_soc", with_trip=True), sm=hass.states) is False

    hass.states.async_set("calendar.ev_trips", "off")

    assert schema_config_available(_ev_schema("sensor.ev_soc", with_trip=True), sm=hass.states) is True
