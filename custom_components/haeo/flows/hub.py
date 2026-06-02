"""Hub configuration flow for HAEO integration."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, ConfigSubentryFlow
from homeassistant.core import callback
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, ELEMENT_TYPE_NETWORK, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON,
    CONF_NAME,
)
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.node import CONF_IS_SINK, CONF_IS_SOURCE
from custom_components.haeo.core.schema.elements.node import SECTION_ROLE as NODE_SECTION_ROLE

from . import (
    HUB_SECTION_ADVANCED,
    HUB_SECTION_COMMON,
    build_hub_entry_data,
    get_element_flow_classes,
    get_hub_setup_schema,
)
from .horizon_schema import is_horizon_entity_selection, preprocess_horizon_input, validate_horizon_entity
from .options import HubOptionsFlow

_LOGGER = logging.getLogger(__name__)


class HubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HAEO hub creation."""

    VERSION = 1
    MINOR_VERSION = 4

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._user_input: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step for hub creation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            hub_name = user_input[HUB_SECTION_COMMON][CONF_NAME]
            existing_names = [entry.title for entry in self.hass.config_entries.async_entries(DOMAIN)]

            if hub_name in existing_names:
                errors[CONF_NAME] = "name_exists"
            else:
                horizon_raw = user_input[HUB_SECTION_COMMON].get(CONF_HORIZON)
                horizon_processed = preprocess_horizon_input(horizon_raw)
                if is_horizon_entity_selection(horizon_processed):
                    entity_id = horizon_processed[0] if isinstance(horizon_processed, list) else horizon_processed
                    try:
                        validate_horizon_entity(self.hass, entity_id)
                    except vol.Invalid:
                        errors[CONF_HORIZON] = "invalid_horizon_entity"

            if not errors:
                await self.async_set_unique_id(f"haeo_hub_{hub_name.lower().replace(' ', '_')}")
                self._abort_if_unique_id_configured()
                self._user_input = user_input
                return await self._create_hub_entry()

        translations = await async_get_translations(
            self.hass, self.hass.config.language, "common", integrations=[DOMAIN]
        )
        default_hub_name = translations.get(f"component.{DOMAIN}.common.default_hub_name", "Home")

        return self.async_show_form(
            step_id="user",
            data_schema=get_hub_setup_schema(suggested_name=default_hub_name),
            errors=errors,
        )

    async def _create_hub_entry(self) -> ConfigFlowResult:
        """Create the hub entry with horizon configuration."""
        hub_name = self._user_input[HUB_SECTION_COMMON][CONF_NAME]
        entry_data = build_hub_entry_data(self._user_input, hub_name=hub_name)
        entry_data[CONF_INTEGRATION_TYPE] = INTEGRATION_TYPE_HUB

        translations = await async_get_translations(
            self.hass, self.hass.config.language, "common", integrations=[DOMAIN]
        )
        switchboard_name = translations[f"component.{DOMAIN}.common.switchboard_node_name"]
        network_subentry_name = translations[f"component.{DOMAIN}.common.network_subentry_name"]

        advanced = self._user_input.get(HUB_SECTION_ADVANCED, {})
        default_debounce = entry_data[HUB_SECTION_ADVANCED][CONF_DEBOUNCE_SECONDS]
        entry_data[HUB_SECTION_ADVANCED] = {
            CONF_DEBOUNCE_SECONDS: advanced.get(CONF_DEBOUNCE_SECONDS, default_debounce),
            CONF_ADVANCED_MODE: advanced.get(CONF_ADVANCED_MODE, False),
        }

        return self.async_create_entry(
            title=hub_name,
            data=entry_data,
            subentries=[
                {
                    "data": {
                        CONF_NAME: network_subentry_name,
                        CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK,
                    },
                    "subentry_type": ELEMENT_TYPE_NETWORK,
                    "title": network_subentry_name,
                    "unique_id": None,
                },
                {
                    "data": {
                        CONF_ELEMENT_TYPE: ElementType.NODE,
                        CONF_NAME: switchboard_name,
                        NODE_SECTION_ROLE: {
                            CONF_IS_SOURCE: False,
                            CONF_IS_SINK: False,
                        },
                    },
                    "subentry_type": ElementType.NODE,
                    "title": switchboard_name,
                    "unique_id": None,
                },
            ],
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> HubOptionsFlow:
        """Get the options flow for this handler."""
        _ = config_entry
        return HubOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        advanced_mode = config_entry.data.get(HUB_SECTION_ADVANCED, {}).get(CONF_ADVANCED_MODE, False)
        flow_classes = get_element_flow_classes()

        return {
            element_type: flow_classes[element_type]
            for element_type, entry in ELEMENT_TYPES.items()
            if not entry.advanced or advanced_mode
        }
