"""Options flow for HAEO hub management."""

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import SelectOptionDict, SelectSelector, SelectSelectorConfig, SelectSelectorMode
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_HORIZON_HOURS, CONF_PERIOD_MINUTES
from custom_components.haeo.schema import schema_for_type
from custom_components.haeo.types import ELEMENT_TYPES

from . import get_network_timing_schema

_LOGGER = logging.getLogger(__name__)


class HubOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for HAEO hub."""

    async def async_step_init(self, _user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        # Check if we have participants for conditional menu options
        participants = self.config_entry.data.get("participants", {})

        # Build menu options based on available participants
        menu_options = ["configure_network", "add_participant"]

        if participants:
            menu_options.extend(["edit_participant", "remove_participant"])

        return self.async_show_menu(
            step_id="init",
            menu_options=menu_options,
        )

    async def async_step_configure_network(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Configure network timing parameters."""
        if user_input is not None:
            # Update network timing configuration
            new_data = self.config_entry.data.copy()
            new_data[CONF_HORIZON_HOURS] = user_input[CONF_HORIZON_HOURS]
            new_data[CONF_PERIOD_MINUTES] = user_input[CONF_PERIOD_MINUTES]

            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)

            # Reload the integration once so new timing takes effect
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Show form with network timing configuration
        data_schema = get_network_timing_schema(config_entry=self.config_entry)

        return self.async_show_form(
            step_id="configure_network",
            data_schema=data_schema,
        )

    async def async_step_add_participant(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Add a new participant."""
        if user_input is not None:
            participant_type = user_input["participant_type"]

            # Route to generic configuration step
            return await self.async_step_configure_element(participant_type)

        # Get translations for options
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "options", integrations=["haeo"], config_flow=True
        )

        # Create options with translated labels
        options = [
            SelectOptionDict(value=element_type, label=translations.get(f"entity.device.{element_type}", element_type))
            for element_type in ELEMENT_TYPES
        ]

        # Show participant type selection with proper i18n support
        return self.async_show_form(
            step_id="add_participant",
            data_schema=vol.Schema(
                {
                    vol.Required("participant_type"): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        ),
                    ),
                },
            ),
        )

    async def async_step_configure_element(
        self,
        element_type: str,
        user_input: dict[str, Any] | None = None,
        current_config: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Configure participant."""
        errors: dict[str, str] = {}

        schema = schema_for_type(
            ELEMENT_TYPES[element_type],
            participants=self.config_entry.data.get("participants", {}),
            current_element_name=current_config.get(CONF_NAME) if current_config else None,
        )

        if user_input is not None:
            # Validate user input against schema
            try:
                schema(user_input)
            except vol.Invalid as e:
                errors[CONF_NAME] = "name_exists" if "already exists" in str(e) else "invalid_input"
                if not errors:
                    return self.async_show_form(step_id=f"configure_{element_type}", data_schema=schema, errors=errors)

            # If validation passes, proceed with business logic
            if not errors:
                # Add or update participant in configuration
                # Keep the flattened structure for HA storage
                element_config = {CONF_ELEMENT_TYPE: element_type, **user_input}
                if current_config:
                    return await self._update_participant(current_config[CONF_NAME], element_config)

                return await self._add_participant(user_input.get("name_value"), element_config)

        return self.async_show_form(step_id=f"configure_{element_type}", data_schema=schema, errors=errors)

    async def async_step_edit_participant(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Edit an existing participant."""
        participants = self.config_entry.data.get("participants", {})

        if not participants:
            return self.async_abort(reason="no_participants")

        if user_input is not None:
            participant_name = user_input["participant"]
            participant_config = participants[participant_name]
            participant_type = participant_config.get("type")

            # Route to generic configure step for editing
            return await self.async_step_configure_element(participant_type, current_config=participant_config)

        participant_options = list(participants.keys())

        return self.async_show_form(
            step_id="edit_participant",
            data_schema=vol.Schema(
                {
                    vol.Required("participant"): SelectSelector(
                        SelectSelectorConfig(options=participant_options, mode=SelectSelectorMode.DROPDOWN),
                    ),
                },
            ),
        )

    async def async_step_remove_participant(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Remove a participant."""
        participants = self.config_entry.data.get("participants", {})

        if not participants:
            return self.async_abort(reason="no_participants")

        if user_input is not None:
            participant_name = user_input["participant"]

            # Remove participant from configuration
            new_data = self.config_entry.data.copy()
            new_participants = new_data["participants"].copy()
            del new_participants[participant_name]
            new_data["participants"] = new_participants

            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)

            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Show form for participant selection
        participant_options = list(participants.keys())

        return self.async_show_form(
            step_id="remove_participant",
            data_schema=vol.Schema(
                {
                    vol.Required("participant"): SelectSelector(
                        SelectSelectorConfig(
                            options=participant_options,
                            mode=SelectSelectorMode.DROPDOWN,
                        ),
                    ),
                },
            ),
        )

    async def _add_participant(self, name: str, participant_config: dict[str, Any]) -> FlowResult:
        """Add a participant to the configuration."""
        new_data = self.config_entry.data.copy()
        new_participants = new_data["participants"].copy()
        new_participants[name] = participant_config
        new_data["participants"] = new_participants

        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)

        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        return self.async_create_entry(title="", data={})

    async def _update_participant(self, old_name: str, new_config: dict[str, Any]) -> FlowResult:
        """Update a participant in the configuration."""
        new_data = self.config_entry.data.copy()
        new_participants = new_data["participants"].copy()

        # Remove old participant and add updated one
        if old_name in new_participants:
            del new_participants[old_name]

        new_name = new_config[CONF_NAME]
        new_participants[new_name] = new_config

        new_data["participants"] = new_participants

        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)

        return self.async_create_entry(title="", data={})


# Dynamically create specific configure methods for each element type
def _create_configure_methods() -> None:
    """Create specific configure methods for each element type."""
    for element_type in ELEMENT_TYPES:
        method_name = f"async_step_configure_{element_type}"

        # Only create if it doesn't already exist
        if not hasattr(HubOptionsFlow, method_name):
            # Capture the current values for the closure
            current_elem_type = element_type

            def create_configure_method(elem_type: str = current_elem_type, method_nm: str = method_name) -> Any:
                async def configure_method(
                    self: HubOptionsFlow,
                    user_input: dict[str, Any] | None = None,
                    current_config: dict[str, Any] | None = None,
                ) -> FlowResult:
                    """Configure element."""
                    # Call the generic method with the correct signature
                    return await self.async_step_configure_element(elem_type, user_input, current_config)

                configure_method.__name__ = method_nm
                return configure_method

            # Set the method on the class
            method = create_configure_method()
            setattr(HubOptionsFlow, method_name, method)


# Create the methods when the module is imported
_create_configure_methods()
