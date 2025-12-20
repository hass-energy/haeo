"""Options flow for HAEO hub management."""

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from custom_components.haeo.const import (
    CONF_BLACKOUT_DURATION_HOURS,
    CONF_BLACKOUT_PROTECTION,
    CONF_DEBOUNCE_SECONDS,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    CONF_UPDATE_INTERVAL_MINUTES,
)

from . import get_network_config_schema

_LOGGER = logging.getLogger(__name__)


class HubOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for HAEO hub."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure network timing parameters."""
        if user_input is not None:
            new_data = self.config_entry.data.copy()
            # Tier configuration
            new_data[CONF_TIER_1_COUNT] = user_input[CONF_TIER_1_COUNT]
            new_data[CONF_TIER_1_DURATION] = user_input[CONF_TIER_1_DURATION]
            new_data[CONF_TIER_2_COUNT] = user_input[CONF_TIER_2_COUNT]
            new_data[CONF_TIER_2_DURATION] = user_input[CONF_TIER_2_DURATION]
            new_data[CONF_TIER_3_COUNT] = user_input[CONF_TIER_3_COUNT]
            new_data[CONF_TIER_3_DURATION] = user_input[CONF_TIER_3_DURATION]
            new_data[CONF_TIER_4_COUNT] = user_input[CONF_TIER_4_COUNT]
            new_data[CONF_TIER_4_DURATION] = user_input[CONF_TIER_4_DURATION]
            # Update and debounce settings
            new_data[CONF_UPDATE_INTERVAL_MINUTES] = user_input[CONF_UPDATE_INTERVAL_MINUTES]
            new_data[CONF_DEBOUNCE_SECONDS] = user_input[CONF_DEBOUNCE_SECONDS]
            # Blackout protection settings
            new_data[CONF_BLACKOUT_PROTECTION] = user_input[CONF_BLACKOUT_PROTECTION]
            new_data[CONF_BLACKOUT_DURATION_HOURS] = user_input[CONF_BLACKOUT_DURATION_HOURS]
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        data_schema = get_network_config_schema(config_entry=self.config_entry)
        return self.async_show_form(step_id="init", data_schema=data_schema)
