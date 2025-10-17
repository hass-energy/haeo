"""Options flow for HAEO hub management."""

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from custom_components.haeo.const import CONF_HORIZON_HOURS, CONF_OPTIMIZER, CONF_PERIOD_MINUTES

from . import get_network_config_schema

_LOGGER = logging.getLogger(__name__)


class HubOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for HAEO hub."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure network timing parameters."""
        if user_input is not None:
            new_data = self.config_entry.data.copy()
            new_data[CONF_HORIZON_HOURS] = user_input[CONF_HORIZON_HOURS]
            new_data[CONF_PERIOD_MINUTES] = user_input[CONF_PERIOD_MINUTES]
            new_data[CONF_OPTIMIZER] = user_input.get(CONF_OPTIMIZER, "highs")
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        data_schema = get_network_config_schema(config_entry=self.config_entry)
        return self.async_show_form(step_id="init", data_schema=data_schema)
