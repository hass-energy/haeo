"""Options flow for HAEO hub management."""

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from custom_components.haeo.const import CONF_ADVANCED_MODE, CONF_DEBOUNCE_SECONDS, CONF_HORIZON_PRESET

from . import (
    HORIZON_PRESET_CUSTOM,
    HUB_SECTION_ADVANCED,
    HUB_SECTION_BASIC,
    HUB_SECTION_TIERS,
    get_custom_tiers_schema,
    get_hub_options_schema,
    get_tier_config,
)

_LOGGER = logging.getLogger(__name__)


class HubOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for HAEO hub."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._user_input: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure hub settings with simplified preset dropdown."""
        if user_input is not None:
            # Store user input for later
            self._user_input = user_input

            # If custom preset selected, go to custom tiers step
            if user_input[HUB_SECTION_BASIC][CONF_HORIZON_PRESET] == HORIZON_PRESET_CUSTOM:
                return await self.async_step_custom_tiers()

            # Otherwise, apply preset values and save
            return await self._save_options()

        data_schema = get_hub_options_schema(config_entry=self.config_entry)
        return self.async_show_form(step_id="init", data_schema=data_schema)

    async def async_step_custom_tiers(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle custom tier configuration step."""
        if user_input is not None:
            # Merge custom tier config with stored user input
            self._user_input[HUB_SECTION_TIERS] = user_input
            return await self._save_options()

        # Show full tier configuration form with current values
        return self.async_show_form(
            step_id="custom_tiers",
            data_schema=get_custom_tiers_schema(config_entry=self.config_entry),
        )

    async def _save_options(self) -> ConfigFlowResult:
        """Save the options with tier configuration."""
        tier_config, stored_preset = get_tier_config(
            self._user_input,
            self._user_input[HUB_SECTION_BASIC].get(CONF_HORIZON_PRESET),
        )

        # Update config entry data with new values
        new_data = {
            **self.config_entry.data,
            HUB_SECTION_BASIC: {
                **self.config_entry.data.get(HUB_SECTION_BASIC, {}),
                CONF_HORIZON_PRESET: stored_preset,
            },
            HUB_SECTION_TIERS: tier_config,
            HUB_SECTION_ADVANCED: {
                **self.config_entry.data.get(HUB_SECTION_ADVANCED, {}),
                CONF_DEBOUNCE_SECONDS: self._user_input[HUB_SECTION_ADVANCED][CONF_DEBOUNCE_SECONDS],
                CONF_ADVANCED_MODE: self._user_input[HUB_SECTION_ADVANCED][CONF_ADVANCED_MODE],
            },
        }

        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
        return self.async_create_entry(title="", data={})
