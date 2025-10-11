"""Hub configuration flow for HAEO integration."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME

from custom_components.haeo.const import CONF_HORIZON_HOURS, CONF_OPTIMIZER, CONF_PERIOD_MINUTES, DOMAIN

from . import get_network_config_schema
from .options import HubOptionsFlow

_LOGGER = logging.getLogger(__name__)


class HubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HAEO hub creation."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step for hub creation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate that the name is unique
            hub_name = user_input[CONF_NAME]
            existing_names = [entry.title for entry in self.hass.config_entries.async_entries(DOMAIN)]

            if hub_name in existing_names:
                errors[CONF_NAME] = "name_exists"
            else:
                # Check unique_id to prevent duplicates
                await self.async_set_unique_id(f"haeo_hub_{hub_name.lower().replace(' ', '_')}")
                self._abort_if_unique_id_configured()

                # Create the hub entry
                return self.async_create_entry(
                    title=hub_name,
                    data={
                        "integration_type": "hub",
                        CONF_NAME: hub_name,
                        CONF_HORIZON_HOURS: user_input[CONF_HORIZON_HOURS],
                        CONF_PERIOD_MINUTES: user_input[CONF_PERIOD_MINUTES],
                        CONF_OPTIMIZER: user_input.get(CONF_OPTIMIZER, "highs"),
                        "participants": {},
                    },
                )

        # Show form with network configuration
        data_schema = get_network_config_schema()

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(_config_entry: ConfigEntry) -> HubOptionsFlow:
        """Get the options flow for this handler."""
        return HubOptionsFlow()
