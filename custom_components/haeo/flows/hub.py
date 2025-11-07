"""Hub configuration flow for HAEO integration."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, ConfigSubentryFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_HORIZON_HOURS,
    CONF_INTEGRATION_TYPE,
    CONF_PERIOD_MINUTES,
    CONF_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.elements import ELEMENT_TYPES

from . import get_network_config_schema
from .element import create_subentry_flow_class
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
                        CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
                        CONF_NAME: hub_name,
                        CONF_HORIZON_HOURS: user_input[CONF_HORIZON_HOURS],
                        CONF_PERIOD_MINUTES: user_input[CONF_PERIOD_MINUTES],
                        CONF_UPDATE_INTERVAL_MINUTES: user_input[CONF_UPDATE_INTERVAL_MINUTES],
                        CONF_DEBOUNCE_SECONDS: user_input[CONF_DEBOUNCE_SECONDS],
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
    def async_get_options_flow(config_entry: ConfigEntry) -> HubOptionsFlow:
        """Get the options flow for this handler."""
        _ = config_entry  # Unused but required by signature
        return HubOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        _ = config_entry  # Unused but required by signature

        # Register regular element flows
        flows: dict[str, type[ConfigSubentryFlow]] = {
            element_type: create_subentry_flow_class(element_type, entry.schema, entry.defaults)
            for element_type, entry in ELEMENT_TYPES.items()
        }

        # Note that the Network element type is not included here as it can't be added/removed like other elements

        return flows
