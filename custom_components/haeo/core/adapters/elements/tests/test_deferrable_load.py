"""Tests for deferrable load adapter availability checks."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.core.schema import as_calendar_value, as_connection_target, as_constant_value
from custom_components.haeo.core.schema.elements import ElementType, deferrable_load
from custom_components.haeo.elements.availability import schema_config_available


async def test_available_with_calendar_and_constants(hass: HomeAssistant) -> None:
    """Calendar values do not gate availability; constants are always available."""
    config: deferrable_load.DeferrableLoadConfigSchema = {
        "element_type": ElementType.DEFERRABLE_LOAD,
        "name": "pump",
        "connection": as_connection_target("switchboard"),
        deferrable_load.SECTION_SCHEDULE: {
            deferrable_load.CONF_WINDOW_CALENDAR: as_calendar_value("calendar.pool_pump"),
        },
        deferrable_load.SECTION_PRICING: {
            deferrable_load.CONF_DEFICIT_PRICE: as_constant_value(10.0),
        },
    }

    assert schema_config_available(config, sm=hass.states) is True
