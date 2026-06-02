"""Options flow for HAEO hub management."""

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
import voluptuous as vol

from custom_components.haeo.core.const import CONF_HORIZON, CONF_NAME

from . import HUB_SECTION_COMMON, build_hub_entry_data, get_hub_options_schema
from .horizon_schema import is_horizon_entity_selection, preprocess_horizon_input, validate_horizon_entity

_LOGGER = logging.getLogger(__name__)


class HubOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for HAEO hub."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._user_input: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure hub settings."""
        if user_input is not None:
            errors: dict[str, str] = {}
            horizon_raw = user_input[HUB_SECTION_COMMON].get(CONF_HORIZON)
            horizon_processed = preprocess_horizon_input(horizon_raw)
            if is_horizon_entity_selection(horizon_processed):
                entity_id = horizon_processed[0] if isinstance(horizon_processed, list) else horizon_processed
                try:
                    validate_horizon_entity(self.hass, entity_id, config_entry=self.config_entry)
                except vol.Invalid:
                    errors[CONF_HORIZON] = "invalid_horizon_entity"

            if errors:
                return self.async_show_form(
                    step_id="init",
                    data_schema=get_hub_options_schema(config_entry=self.config_entry),
                    errors=errors,
                )

            self._user_input = user_input
            return await self._save_options()

        return self.async_show_form(
            step_id="init",
            data_schema=get_hub_options_schema(config_entry=self.config_entry),
        )

    async def _save_options(self) -> ConfigFlowResult:
        """Save the options with horizon configuration."""
        hub_name = self.config_entry.data.get(HUB_SECTION_COMMON, {}).get(CONF_NAME, self.config_entry.title)
        new_data = build_hub_entry_data(
            self._user_input,
            hub_name=hub_name,
            existing_data=dict(self.config_entry.data),
        )

        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
        return self.async_create_entry(title="", data={})
