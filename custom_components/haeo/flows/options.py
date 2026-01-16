"""Options flow for HAEO hub management."""

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from custom_components.haeo.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_HORIZON_DURATION_MINUTES,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_DURATION,
    CONF_UPDATE_INTERVAL_MINUTES,
)

from . import (
    convert_horizon_days_to_minutes,
    get_custom_tiers_schema,
    get_default_tier_config,
    get_hub_options_schema,
)

_LOGGER = logging.getLogger(__name__)


class HubOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for HAEO hub."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._user_input: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure hub settings with horizon duration selector."""
        if user_input is not None:
            # Convert horizon_days to horizon_duration_minutes
            user_input = convert_horizon_days_to_minutes(user_input)

            # Store user input for later
            self._user_input = user_input

            # Save options with updated horizon
            return await self._save_options()

        data_schema = get_hub_options_schema(config_entry=self.config_entry)
        return self.async_show_form(step_id="init", data_schema=data_schema)

    async def async_step_custom_tiers(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle custom tier configuration step."""
        if user_input is not None:
            # Merge custom tier config with stored user input
            self._user_input.update(user_input)
            return await self._save_options()

        # Show tier configuration form with current values
        return self.async_show_form(
            step_id="custom_tiers",
            data_schema=get_custom_tiers_schema(config_entry=self.config_entry),
        )

    async def _save_options(self) -> ConfigFlowResult:
        """Save the options with tier configuration."""
        # Get default tier config with updated horizon
        horizon_minutes = self._user_input.get(CONF_HORIZON_DURATION_MINUTES)
        tier_config = get_default_tier_config(horizon_minutes)

        # Override with any custom tier values from user input
        for key in [
            CONF_TIER_1_COUNT,
            CONF_TIER_1_DURATION,
            CONF_TIER_2_COUNT,
            CONF_TIER_2_DURATION,
            CONF_TIER_3_COUNT,
            CONF_TIER_3_DURATION,
            CONF_TIER_4_DURATION,
        ]:
            if key in self._user_input:
                tier_config[key] = self._user_input[key]

        # Update config entry data with new values
        new_data = {
            **self.config_entry.data,
            **tier_config,
            CONF_UPDATE_INTERVAL_MINUTES: self._user_input[CONF_UPDATE_INTERVAL_MINUTES],
            CONF_DEBOUNCE_SECONDS: self._user_input[CONF_DEBOUNCE_SECONDS],
            CONF_ADVANCED_MODE: self._user_input[CONF_ADVANCED_MODE],
        }

        # Remove legacy keys if present
        new_data.pop("horizon_preset", None)
        new_data.pop("tier_4_count", None)

        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
        return self.async_create_entry(title="", data={})
