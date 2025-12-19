"""Hub configuration flow for HAEO integration."""

import logging
from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.translation import async_get_translations

from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON_PRESET,
    CONF_INTEGRATION_TYPE,
    CONF_TIER_1_DURATION,
    CONF_TIER_1_UNTIL,
    CONF_TIER_2_DURATION,
    CONF_TIER_2_UNTIL,
    CONF_TIER_3_DURATION,
    CONF_TIER_3_UNTIL,
    CONF_TIER_4_DURATION,
    CONF_TIER_4_UNTIL,
    CONF_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.elements import ELEMENT_TYPE_NODE, ELEMENT_TYPES

from . import (
    HORIZON_PRESET_CUSTOM,
    HORIZON_PRESETS,
    get_custom_tiers_schema,
    get_hub_setup_schema,
)
from .element import create_subentry_flow_class
from .options import HubOptionsFlow

_LOGGER = logging.getLogger(__name__)


class HubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HAEO hub creation."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._user_input: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step for hub creation with simplified options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate that the name is unique
            hub_name = user_input[CONF_NAME]
            existing_names = [
                entry.title for entry in self.hass.config_entries.async_entries(DOMAIN)
            ]

            if hub_name in existing_names:
                errors[CONF_NAME] = "name_exists"
            else:
                # Check unique_id to prevent duplicates
                await self.async_set_unique_id(
                    f"haeo_hub_{hub_name.lower().replace(' ', '_')}"
                )
                self._abort_if_unique_id_configured()

                # Store user input for later
                self._user_input = user_input

                # If custom preset selected, go to custom tiers step
                if user_input[CONF_HORIZON_PRESET] == HORIZON_PRESET_CUSTOM:
                    return await self.async_step_custom_tiers()

                # Otherwise, create entry with preset values
                return await self._create_hub_entry()

        # Show simplified form with horizon preset dropdown
        return self.async_show_form(
            step_id="user",
            data_schema=get_hub_setup_schema(),
            errors=errors,
        )

    async def async_step_custom_tiers(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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

        # Resolve the switchboard node name from translations
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "common", integrations=[DOMAIN]
        )
        switchboard_name = translations[
            f"component.{DOMAIN}.common.switchboard_node_name"
        ]

        # Create the hub entry with initial subentries
        return self.async_create_entry(
            title=hub_name,
            data={
                CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
                CONF_NAME: hub_name,
                # Store the chosen preset for the options flow
                CONF_HORIZON_PRESET: stored_preset,
                # Tier configuration
                CONF_TIER_1_DURATION: tier_config[CONF_TIER_1_DURATION],
                CONF_TIER_1_UNTIL: tier_config[CONF_TIER_1_UNTIL],
                CONF_TIER_2_DURATION: tier_config[CONF_TIER_2_DURATION],
                CONF_TIER_2_UNTIL: tier_config[CONF_TIER_2_UNTIL],
                CONF_TIER_3_DURATION: tier_config[CONF_TIER_3_DURATION],
                CONF_TIER_3_UNTIL: tier_config[CONF_TIER_3_UNTIL],
                CONF_TIER_4_DURATION: tier_config[CONF_TIER_4_DURATION],
                CONF_TIER_4_UNTIL: tier_config[CONF_TIER_4_UNTIL],
                # Update and debounce settings
                CONF_UPDATE_INTERVAL_MINUTES: self._user_input[
                    CONF_UPDATE_INTERVAL_MINUTES
                ],
                CONF_DEBOUNCE_SECONDS: self._user_input[CONF_DEBOUNCE_SECONDS],
            },
            subentries=[
                # Network subentry for optimization sensors
                {
                    "data": {
                        CONF_NAME: hub_name,
                        CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK,
                    },
                    "subentry_type": ELEMENT_TYPE_NETWORK,
                    "title": hub_name,
                    "unique_id": None,
                },
                # Switchboard node as central connection point
                {
                    "data": {
                        CONF_NAME: switchboard_name,
                        CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE,
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
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        _ = config_entry  # Unused but required by signature

        # Register regular element flows
        flows: dict[str, type[ConfigSubentryFlow]] = {
            element_type: create_subentry_flow_class(
                element_type, entry.schema, entry.defaults
            )
            for element_type, entry in ELEMENT_TYPES.items()
        }

        # Note that the Network subentry is not included here as it can't be added/removed like other elements

        return flows
