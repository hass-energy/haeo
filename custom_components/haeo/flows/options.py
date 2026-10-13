"""Options flow for HAEO hub management."""

import logging
from typing import Any  # noqa: TID251  # HA flow signatures are Any-typed upstream

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from custom_components.haeo.const import CONF_RECORD_FORECASTS
from custom_components.haeo.core.const import CONF_ADVANCED_MODE, CONF_DEBOUNCE_SECONDS, CONF_HORIZON
from custom_components.haeo.flows.horizon import validate_horizon

from . import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON, get_hub_options_schema

_LOGGER = logging.getLogger(__name__)


class HubOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for HAEO hub."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure hub settings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            horizon = user_input[HUB_SECTION_COMMON][CONF_HORIZON]
            validate_horizon(self.hass, horizon, errors, entry_id=self.config_entry.entry_id)
            if not errors:
                advanced = user_input[HUB_SECTION_ADVANCED]
                new_data = {
                    **self.config_entry.data,
                    HUB_SECTION_COMMON: {**self.config_entry.data[HUB_SECTION_COMMON], CONF_HORIZON: horizon},
                    HUB_SECTION_ADVANCED: {
                        **self.config_entry.data.get(HUB_SECTION_ADVANCED, {}),
                        CONF_DEBOUNCE_SECONDS: advanced[CONF_DEBOUNCE_SECONDS],
                        CONF_ADVANCED_MODE: advanced[CONF_ADVANCED_MODE],
                    },
                    CONF_RECORD_FORECASTS: advanced.get(CONF_RECORD_FORECASTS, False),
                }
                self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
                return self.async_create_entry(title="", data={})

        data_schema = get_hub_options_schema(config_entry=self.config_entry)
        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors)
