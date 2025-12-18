"""Hub configuration flow for HAEO integration."""

import logging
from typing import Any, OrderedDict

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, ConfigSubentryFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.translation import async_get_translations

from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_INTEGRATION_TYPE,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    CONF_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.elements import ELEMENT_TYPE_NODE, ELEMENT_TYPES

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

                # Resolve the switchboard node name from translations
                translations = await async_get_translations(
                    self.hass, self.hass.config.language, "common", integrations=[DOMAIN]
                )
                switchboard_name = translations[f"component.{DOMAIN}.common.switchboard_node_name"]

                # Create the hub entry with initial subentries
                return self.async_create_entry(
                    title=hub_name,
                    data={
                        CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
                        CONF_NAME: hub_name,
                        # Tier 1: Fine-grained near-term intervals
                        CONF_TIER_1_COUNT: user_input[CONF_TIER_1_COUNT],
                        CONF_TIER_1_DURATION: user_input[CONF_TIER_1_DURATION],
                        # Tier 2: Short-term intervals
                        CONF_TIER_2_COUNT: user_input[CONF_TIER_2_COUNT],
                        CONF_TIER_2_DURATION: user_input[CONF_TIER_2_DURATION],
                        # Tier 3: Medium-term intervals
                        CONF_TIER_3_COUNT: user_input[CONF_TIER_3_COUNT],
                        CONF_TIER_3_DURATION: user_input[CONF_TIER_3_DURATION],
                        # Tier 4: Long-term intervals
                        CONF_TIER_4_COUNT: user_input[CONF_TIER_4_COUNT],
                        CONF_TIER_4_DURATION: user_input[CONF_TIER_4_DURATION],
                        # Update and debounce settings
                        CONF_UPDATE_INTERVAL_MINUTES: user_input[CONF_UPDATE_INTERVAL_MINUTES],
                        CONF_DEBOUNCE_SECONDS: user_input[CONF_DEBOUNCE_SECONDS],
                    },
                    subentries=[
                        # Network subentry for optimization sensors
                        {
                            "data": {CONF_NAME: hub_name, CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK},
                            "subentry_type": ELEMENT_TYPE_NETWORK,
                            "title": hub_name,
                            "unique_id": None,
                        },
                        # Switchboard node as central connection point
                        {
                            "data": {CONF_NAME: switchboard_name, CONF_ELEMENT_TYPE: ELEMENT_TYPE_NODE},
                            "subentry_type": ELEMENT_TYPE_NODE,
                            "title": switchboard_name,
                            "unique_id": None,
                        },
                    ],
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
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> OrderedDict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        _ = config_entry  # Unused but required by signature

        # Register regular element flows
        flows: OrderedDict[str, type[ConfigSubentryFlow]] = OrderedDict(
            {
                element_type: create_subentry_flow_class(element_type, entry.schema, entry.defaults)
                for element_type, entry in ELEMENT_TYPES.items()
            }
        )

        # Note that the Network subentry is not included here as it can't be added/removed like other elements

        return flows
