"""Options flow for HAEO hub management."""

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_HORIZON_PRESET,
    CONF_TIER_1_DURATION,
    CONF_TIER_1_UNTIL,
    CONF_TIER_2_DURATION,
    CONF_TIER_2_UNTIL,
    CONF_TIER_3_DURATION,
    CONF_TIER_3_UNTIL,
    CONF_TIER_4_DURATION,
    CONF_TIER_4_UNTIL,
    CONF_UPDATE_INTERVAL_MINUTES,
)

from . import (
    HORIZON_PRESET_CUSTOM,
    HORIZON_PRESETS,
    get_custom_tiers_schema,
    get_hub_options_schema,
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
            if user_input[CONF_HORIZON_PRESET] == HORIZON_PRESET_CUSTOM:
                return await self.async_step_custom_tiers()

            # Otherwise, apply preset values and save
            return await self._save_options()

        data_schema = get_hub_options_schema(config_entry=self.config_entry)
        return self.async_show_form(step_id="init", data_schema=data_schema)

    async def async_step_custom_tiers(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle custom tier configuration step."""
        if user_input is not None:
            # Merge custom tier config with stored user input
            self._user_input.update(user_input)
            return await self._save_options()

        # Show full tier configuration form with current values
        return self.async_show_form(
            step_id="custom_tiers",
            data_schema=get_custom_tiers_schema(config_entry=self.config_entry),
        )

    async def _save_options(self) -> ConfigFlowResult:
        """Save the options with tier configuration."""
        horizon_preset = self._user_input.get(CONF_HORIZON_PRESET)

        # Get tier values from preset or from custom input
        if horizon_preset and horizon_preset != HORIZON_PRESET_CUSTOM:
            tier_config = HORIZON_PRESETS[horizon_preset]
            stored_preset = horizon_preset
        else:
            # Custom values were provided in _user_input
            tier_config = {
                CONF_TIER_1_DURATION: self._user_input[CONF_TIER_1_DURATION],
                CONF_TIER_1_UNTIL: self._user_input[CONF_TIER_1_UNTIL],
                CONF_TIER_2_DURATION: self._user_input[CONF_TIER_2_DURATION],
                CONF_TIER_2_UNTIL: self._user_input[CONF_TIER_2_UNTIL],
                CONF_TIER_3_DURATION: self._user_input[CONF_TIER_3_DURATION],
                CONF_TIER_3_UNTIL: self._user_input[CONF_TIER_3_UNTIL],
                CONF_TIER_4_DURATION: self._user_input[CONF_TIER_4_DURATION],
                CONF_TIER_4_UNTIL: self._user_input[CONF_TIER_4_UNTIL],
            }
            stored_preset = HORIZON_PRESET_CUSTOM

        # Update config entry data with new values
        new_data = self.config_entry.data.copy()
        new_data[CONF_HORIZON_PRESET] = stored_preset
        new_data[CONF_TIER_1_DURATION] = tier_config[CONF_TIER_1_DURATION]
        new_data[CONF_TIER_1_UNTIL] = tier_config[CONF_TIER_1_UNTIL]
        new_data[CONF_TIER_2_DURATION] = tier_config[CONF_TIER_2_DURATION]
        new_data[CONF_TIER_2_UNTIL] = tier_config[CONF_TIER_2_UNTIL]
        new_data[CONF_TIER_3_DURATION] = tier_config[CONF_TIER_3_DURATION]
        new_data[CONF_TIER_3_UNTIL] = tier_config[CONF_TIER_3_UNTIL]
        new_data[CONF_TIER_4_DURATION] = tier_config[CONF_TIER_4_DURATION]
        new_data[CONF_TIER_4_UNTIL] = tier_config[CONF_TIER_4_UNTIL]
        new_data[CONF_UPDATE_INTERVAL_MINUTES] = self._user_input[CONF_UPDATE_INTERVAL_MINUTES]
        new_data[CONF_DEBOUNCE_SECONDS] = self._user_input[CONF_DEBOUNCE_SECONDS]

        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
        return self.async_create_entry(title="", data={})
