"""Tests for schedulable load adapter availability checks."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.core.schema import as_calendar_value, as_connection_target, as_constant_value
from custom_components.haeo.core.schema.elements import ElementType, schedulable_load
from custom_components.haeo.elements.availability import schema_config_available


async def test_available_with_calendar_and_constants(hass: HomeAssistant) -> None:
    """Calendar values do not gate availability; constants are always available."""
    config: schedulable_load.SchedulableLoadConfigSchema = {
        "element_type": ElementType.SCHEDULABLE_LOAD,
        "name": "dishwasher",
        "connection": as_connection_target("switchboard"),
        schedulable_load.SECTION_SCHEDULE: {
            schedulable_load.CONF_WINDOW_CALENDAR: as_calendar_value("calendar.dishwasher"),
        },
        schedulable_load.SECTION_PROFILE: {
            schedulable_load.CONF_POWER: as_constant_value(1.8),
            schedulable_load.CONF_DURATION: as_constant_value(2.5),
        },
        schedulable_load.SECTION_PRICING: {
            schedulable_load.CONF_DEFICIT_PRICE: as_constant_value(10.0),
        },
    }

    assert schema_config_available(config, sm=hass.states) is True
