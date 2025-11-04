"""Network subentry flow for HAEO integration."""

from typing import Any

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers import selector
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, ELEMENT_TYPE_NETWORK
from custom_components.haeo.network import evaluate_network_connectivity


class NetworkSubentryFlow(ConfigSubentryFlow):
    """Config flow for the Network subentry.

    The network is a special subentry that:
    - Is auto-created with each hub
    - Contains optimization sensors
    - Cannot be deleted (only reconfigured)
    - Does not participate in connections
    """

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle network creation (should rarely be called directly)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors[CONF_NAME] = "missing_name"
            else:
                hub_entry = self._get_entry()

                # Check if network already exists
                for subentry in hub_entry.subentries.values():
                    if subentry.subentry_type == ELEMENT_TYPE_NETWORK:
                        errors[CONF_NAME] = "network_exists"
                        break

            if not errors:
                hub_entry = self._get_entry()
                evaluate_network_connectivity(self.hass, hub_entry)
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK,
                        CONF_NAME: name,
                    },
                )

        # Simple schema with just name
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Network"): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Reconfigure the network name."""
        subentry = self._get_reconfigure_subentry()
        current_name = subentry.data.get(CONF_NAME)
        errors: dict[str, str] = {}

        if user_input is not None:
            new_name = user_input.get(CONF_NAME)
            if not new_name:
                errors[CONF_NAME] = "missing_name"

            if not errors:
                hub_entry = self._get_entry()
                evaluate_network_connectivity(self.hass, hub_entry)
                return self.async_update_reload_and_abort(
                    hub_entry,
                    subentry,
                    title=str(new_name),
                    data={
                        CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK,
                        CONF_NAME: new_name,
                    },
                )

        # Simple schema with just name
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=current_name): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
            }
        )

        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)
