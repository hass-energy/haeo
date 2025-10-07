"""Hub configuration flow for HAEO integration."""

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from custom_components.haeo.const import CONF_HORIZON_HOURS, CONF_PERIOD_MINUTES, DOMAIN

from .options import HubOptionsFlow

from . import get_network_timing_schema, validate_network_timing_input

_LOGGER = logging.getLogger(__name__)


class HubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HAEO hub creation."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step for hub creation."""
        if user_input is not None:
            # Validate input using shared function
            errors, validated_data = validate_network_timing_input(
                user_input,
                hass=self.hass,
                include_name=True,
                name_required=True,
            )

            if errors:
                data_schema = get_network_timing_schema(include_name=True, name_required=True)
                return self.async_show_form(
                    step_id="user",
                    data_schema=data_schema,
                    errors=errors,
                )

            hub_name = validated_data["name"]

            # Create the hub entry
            await self.async_set_unique_id(f"haeo_hub_{hub_name.lower().replace(' ', '_')}")
            self._abort_if_unique_id_configured()

            # Create the hub entry
            return self.async_create_entry(
                title=hub_name,
                data={
                    "integration_type": "hub",
                    CONF_NAME: hub_name,
                    CONF_HORIZON_HOURS: validated_data[CONF_HORIZON_HOURS],
                    CONF_PERIOD_MINUTES: validated_data[CONF_PERIOD_MINUTES],
                    "participants": {},
                },
            )

        # Show form with network timing configuration
        data_schema = get_network_timing_schema(include_name=True, name_required=True)

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
        )

    @staticmethod
    def async_get_options_flow(_config_entry: ConfigEntry) -> HubOptionsFlow:
        """Get the options flow for this handler."""
        return HubOptionsFlow()
