"""Hub configuration flow for HAEO integration."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, ConfigSubentryFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.translation import async_get_translations

from custom_components.haeo.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON_DURATION_MINUTES,
    CONF_INTEGRATION_TYPE,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.elements import ELEMENT_TYPE_NODE, ELEMENT_TYPES
from custom_components.haeo.elements.node import CONF_IS_SINK, CONF_IS_SOURCE

from . import convert_horizon_days_to_minutes, get_custom_tiers_schema, get_default_tier_config, get_hub_setup_schema
from .options import HubOptionsFlow

_LOGGER = logging.getLogger(__name__)


class HubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HAEO hub creation."""

    VERSION = 2
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._user_input: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step for hub creation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Convert horizon_days to horizon_duration_minutes
            user_input = convert_horizon_days_to_minutes(user_input)

            # Validate that the name is unique
            hub_name = user_input[CONF_NAME]
            existing_names = [entry.title for entry in self.hass.config_entries.async_entries(DOMAIN)]

            if hub_name in existing_names:
                errors[CONF_NAME] = "name_exists"
            else:
                # Check unique_id to prevent duplicates
                await self.async_set_unique_id(f"haeo_hub_{hub_name.lower().replace(' ', '_')}")
                self._abort_if_unique_id_configured()

                # Store user input for later
                self._user_input = user_input

                # Create entry with default tier values
                return await self._create_hub_entry()

        # Fetch the default hub name from translations
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "common", integrations=[DOMAIN]
        )
        default_hub_name = translations.get(f"component.{DOMAIN}.common.default_hub_name", "Home")

        # Show simplified form with horizon duration selector
        return self.async_show_form(
            step_id="user",
            data_schema=get_hub_setup_schema(suggested_name=default_hub_name),
            errors=errors,
        )

    async def async_step_custom_tiers(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle custom tier configuration step."""
        if user_input is not None:
            # Merge custom tier config with stored user input
            self._user_input.update(user_input)
            return await self._create_hub_entry()

        # Show full tier configuration form
        return self.async_show_form(
            step_id="custom_tiers",
            data_schema=get_custom_tiers_schema(),
        )

    async def _create_hub_entry(self) -> ConfigFlowResult:
        """Create the hub entry with tier configuration."""
        hub_name = self._user_input[CONF_NAME]

        # Get tier config - use horizon from user input
        horizon_minutes = self._user_input.get(CONF_HORIZON_DURATION_MINUTES)
        tier_config = get_default_tier_config(horizon_minutes)

        # Override with any custom tier values
        for key in tier_config:
            if key in self._user_input:
                tier_config[key] = self._user_input[key]

        # Resolve the switchboard node name from translations
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "common", integrations=[DOMAIN]
        )
        switchboard_name = translations[f"component.{DOMAIN}.common.switchboard_node_name"]
        network_subentry_name = translations[f"component.{DOMAIN}.common.network_subentry_name"]

        # Create the hub entry with initial subentries
        return self.async_create_entry(
            title=hub_name,
            data={
                CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
                CONF_NAME: hub_name,
                **tier_config,
                CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
                CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
                CONF_ADVANCED_MODE: self._user_input[CONF_ADVANCED_MODE],
            },
            subentries=[
                # Network subentry for optimization sensors
                {
                    "data": {
                        CONF_NAME: network_subentry_name,
                        CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK,
                    },
                    "subentry_type": ELEMENT_TYPE_NETWORK,
                    "title": network_subentry_name,
                    "unique_id": None,
                },
                # Switchboard node as central connection point
                {
                    "data": {
                        CONF_NAME: switchboard_name,
                        CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE,
                        CONF_IS_SOURCE: False,
                        CONF_IS_SINK: False,
                    },
                    "subentry_type": ELEMENT_TYPE_NODE,
                    "title": switchboard_name,
                    "unique_id": None,
                },
            ],
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> HubOptionsFlow:
        """Get the options flow for this handler."""
        _ = config_entry  # Unused but required by signature
        return HubOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration.

        Element types marked as advanced in the registry require advanced_mode enabled.
        """
        advanced_mode = config_entry.data.get(CONF_ADVANCED_MODE, False)

        # Register element flows, filtering advanced types based on mode
        return {
            element_type: entry.flow_class
            for element_type, entry in ELEMENT_TYPES.items()
            if not entry.advanced or advanced_mode
        }
