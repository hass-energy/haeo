"""Hub configuration flow for HAEO integration."""

import logging
from typing import Any  # noqa: TID251  # HA flow signatures are Any-typed upstream

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryData,
    ConfigSubentryFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.translation import async_get_translations

from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, ELEMENT_TYPE_NETWORK, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON,
    DEFAULT_DEBOUNCE_SECONDS,
)
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.flows.horizon import async_horizon_preset_labels, validate_horizon
from custom_components.haeo.migrations import MIGRATION_MINOR_VERSION

from . import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON, get_element_flow_classes, get_hub_setup_schema
from .options import HubOptionsFlow, async_hub_settings_schema, hub_settings_data, validate_hub_settings

_LOGGER = logging.getLogger(__name__)


async def async_common_name(hass: HomeAssistant, key: str) -> str:
    """Return a name from the translations' common strings in the configured language."""
    translations = await async_get_translations(hass, hass.config.language, "common", integrations=[DOMAIN])
    return translations[f"component.{DOMAIN}.common.{key}"]


def _named_subentry(element_type: str, name: str) -> ConfigSubentryData:
    """Return the data of a subentry that holds only its element type and name."""
    return {
        "data": {CONF_NAME: name, CONF_ELEMENT_TYPE: element_type},
        "subentry_type": element_type,
        "title": name,
        "unique_id": None,
    }


async def async_network_subentry(hass: HomeAssistant) -> ConfigSubentryData:
    """Return the network subentry, which holds the optimization sensors."""
    return _named_subentry(ELEMENT_TYPE_NETWORK, await async_common_name(hass, "network_subentry_name"))


async def async_switchboard_subentry(hass: HomeAssistant) -> ConfigSubentryData:
    """Return the switchboard junction, the central point other elements connect to."""
    return _named_subentry(ElementType.JUNCTION, await async_common_name(hass, "switchboard_node_name"))


class HubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HAEO hub creation."""

    VERSION = 1
    MINOR_VERSION = MIGRATION_MINOR_VERSION

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step for hub creation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate that the name is unique
            hub_name = user_input[HUB_SECTION_COMMON][CONF_NAME]
            existing_names = [entry.title for entry in self.hass.config_entries.async_entries(DOMAIN)]

            # The name and horizon fields sit in a section, and Home Assistant only shows top-level field errors
            if hub_name in existing_names:
                errors[HUB_SECTION_COMMON] = "name_exists"
            else:
                validate_horizon(
                    self.hass,
                    user_input[HUB_SECTION_COMMON][CONF_HORIZON],
                    errors,
                    error_key=HUB_SECTION_COMMON,
                    entry_id=None,
                )
            if not errors:
                # Check unique_id to prevent duplicates
                await self.async_set_unique_id(f"haeo_hub_{hub_name.lower().replace(' ', '_')}")
                self._abort_if_unique_id_configured()
                return await self._create_hub_entry(user_input)

        default_hub_name = await async_common_name(self.hass, "default_hub_name")

        return self.async_show_form(
            step_id="user",
            data_schema=get_hub_setup_schema(
                await async_horizon_preset_labels(self.hass), suggested_name=default_hub_name
            ),
            errors=errors,
        )

    async def _create_hub_entry(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        """Create the hub entry from the validated setup form."""
        common = user_input[HUB_SECTION_COMMON]
        hub_name = common[CONF_NAME]

        # Create the hub entry with initial subentries
        return self.async_create_entry(
            title=hub_name,
            data={
                CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
                HUB_SECTION_COMMON: {
                    CONF_NAME: hub_name,
                    CONF_HORIZON: common[CONF_HORIZON],
                },
                HUB_SECTION_ADVANCED: {
                    CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
                    CONF_ADVANCED_MODE: user_input[HUB_SECTION_ADVANCED][CONF_ADVANCED_MODE],
                },
            },
            subentries=[await async_network_subentry(self.hass), await async_switchboard_subentry(self.hass)],
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Edit the hub settings, using the same form as the options flow."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = validate_hub_settings(self.hass, entry, user_input)
            if not errors:
                data = hub_settings_data(entry, user_input)
                # A loaded hub's update listener reloads it when its data changes, so
                # reloading here as well would reload it twice. A hub that has not set
                # up has no listener, so it is reloaded here to apply the settings.
                if entry.state is ConfigEntryState.LOADED:
                    return self.async_update_and_abort(entry, data=data)
                return self.async_update_reload_and_abort(entry, data=data)

        data_schema = await async_hub_settings_schema(self.hass, entry)
        return self.async_show_form(step_id="reconfigure", data_schema=data_schema, errors=errors)

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
        advanced_mode = config_entry.data.get(HUB_SECTION_ADVANCED, {}).get(CONF_ADVANCED_MODE, False)
        flow_classes = get_element_flow_classes()

        # Register element flows, filtering advanced types based on mode
        return {
            element_type: flow_classes[element_type]
            for element_type, entry in ELEMENT_TYPES.items()
            if not entry.advanced or advanced_mode
        }
