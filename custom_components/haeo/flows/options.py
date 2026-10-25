"""Options flow for HAEO hub management."""

from collections.abc import Mapping
import logging
from typing import Any  # noqa: TID251  # HA flow signatures are Any-typed upstream

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.core import HomeAssistant
import voluptuous as vol

from custom_components.haeo.const import CONF_RECORD_FORECASTS
from custom_components.haeo.core.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_HORIZON,
    CONF_RELAX_INFEASIBLE,
)
from custom_components.haeo.flows.horizon import async_horizon_preset_labels, validate_horizon

from . import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON, get_hub_options_schema

_LOGGER = logging.getLogger(__name__)


def validate_hub_settings(hass: HomeAssistant, entry: ConfigEntry, user_input: Mapping[str, Any]) -> dict[str, str]:
    """Return the form errors for submitted hub settings."""
    errors: dict[str, str] = {}
    validate_horizon(
        hass,
        user_input[HUB_SECTION_COMMON][CONF_HORIZON],
        errors,
        error_key=HUB_SECTION_COMMON,
        entry_id=entry.entry_id,
    )
    return errors


def hub_settings_data(entry: ConfigEntry, user_input: Mapping[str, Any]) -> dict[str, Any]:
    """Return the hub entry data with the submitted hub settings applied."""
    advanced = user_input[HUB_SECTION_ADVANCED]
    return {
        **entry.data,
        HUB_SECTION_COMMON: {
            **entry.data[HUB_SECTION_COMMON],
            CONF_HORIZON: user_input[HUB_SECTION_COMMON][CONF_HORIZON],
        },
        HUB_SECTION_ADVANCED: {
            **entry.data.get(HUB_SECTION_ADVANCED, {}),
            CONF_DEBOUNCE_SECONDS: advanced[CONF_DEBOUNCE_SECONDS],
            CONF_ADVANCED_MODE: advanced[CONF_ADVANCED_MODE],
            CONF_RELAX_INFEASIBLE: advanced[CONF_RELAX_INFEASIBLE],
        },
        CONF_RECORD_FORECASTS: advanced.get(CONF_RECORD_FORECASTS, False),
    }


async def async_hub_settings_schema(hass: HomeAssistant, entry: ConfigEntry) -> vol.Schema:
    """Return the hub settings form schema, defaulting to the entry's current settings."""
    return get_hub_options_schema(entry, await async_horizon_preset_labels(hass))


class HubOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for HAEO hub."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure hub settings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = validate_hub_settings(self.hass, self.config_entry, user_input)
            if not errors:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=hub_settings_data(self.config_entry, user_input)
                )
                return self.async_create_entry(title="", data={})

        data_schema = await async_hub_settings_schema(self.hass, self.config_entry)
        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors)
