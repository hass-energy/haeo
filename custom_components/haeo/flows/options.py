"""Options flow for HAEO hub management."""

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_HORIZON_HOURS, CONF_OPTIMIZER, CONF_PERIOD_MINUTES
from custom_components.haeo.schema import schema_for_type
from custom_components.haeo.types import ELEMENT_TYPES

from . import get_network_config_schema

_LOGGER = logging.getLogger(__name__)


class HubOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for HAEO hub."""

    async def async_step_init(self, _user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
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

    async def async_step_configure_network(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure network timing parameters."""
        if user_input is not None:
            # Update network timing configuration
            new_data = self.config_entry.data.copy()
            new_data[CONF_HORIZON_HOURS] = user_input[CONF_HORIZON_HOURS]
            new_data[CONF_PERIOD_MINUTES] = user_input[CONF_PERIOD_MINUTES]
            new_data[CONF_OPTIMIZER] = user_input.get(CONF_OPTIMIZER, "highs")

            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)

            # Reload the integration once so new timing takes effect
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Show form with network configuration
        data_schema = get_network_config_schema(config_entry=self.config_entry)

        return self.async_show_form(
            step_id="configure_network",
            data_schema=data_schema,
        )

    async def async_step_add_participant(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Add a new participant."""
        if user_input is not None:
            participant_type = user_input["participant_type"]

            # Route to generic configuration step
            return await self.async_step_configure_element(participant_type)

        # Create options list with element types as values
        options = list(ELEMENT_TYPES.keys())

        # Show participant type selection with translation support via selector
        return self.async_show_form(
            step_id="add_participant",
            data_schema=vol.Schema(
                {
                    vol.Required("participant_type"): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="participant_type",
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
    ) -> ConfigFlowResult:
        """Configure participant."""
        errors: dict[str, str] = {}

        schema_cls, _, element_defaults = ELEMENT_TYPES[element_type]
        # Extract current element name for duplicate checking (stored as name_value in flattened config)
        current_element_name = current_config.get("name_value") if current_config else None

        # Flatten element defaults (convert field_name to field_name_value format)
        flattened_defaults = {f"{k}_value": v for k, v in element_defaults.items()}

        # Merge: start with element defaults, override with current config if editing
        merged_defaults = {**flattened_defaults, **(current_config or {})}

        # Create schema with merged defaults
        schema = schema_for_type(
            schema_cls,
            defaults=merged_defaults,
            participants=self.config_entry.data.get("participants", {}),
            current_element_name=current_element_name,
        )

        if user_input is not None:
            # Validate user input against schema
            try:
                schema(user_input)
            except vol.Invalid:
                errors["base"] = "invalid_input"
                _LOGGER.exception("Validation error")

            # Check for duplicate names
            if not errors:
                name = user_input.get("name_value")
                if not name:
                    errors["base"] = "missing_name"
                else:
                    participants = self.config_entry.data.get("participants", {})
                    current_name = current_config.get("name_value") if current_config else None

                    # Check if name already exists (excluding current element when editing)
                    if name in participants and name != current_name:
                        errors["name_value"] = "name_exists"

            # If validation passes, proceed with business logic
            if not errors:
                name = user_input.get("name_value")
                if not name:
                    errors["base"] = "missing_name"
                    return self.async_show_form(
                        step_id=f"configure_{element_type}",
                        data_schema=schema,
                        errors=errors,
                    )

                # Add or update participant in configuration
                # Keep the flattened structure for HA storage
                element_config = {CONF_ELEMENT_TYPE: element_type, **user_input}
                if current_config:
                    old_name = current_config.get("name_value")
                    if not old_name:
                        errors["base"] = "invalid_config"
                        return self.async_show_form(
                            step_id=f"configure_{element_type}",
                            data_schema=schema,
                            errors=errors,
                        )
                    return await self._update_participant(old_name, element_config)

                return await self._add_participant(name, element_config)

        # When showing the form (first time or with errors)
        return self.async_show_form(
            step_id=f"configure_{element_type}",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_edit_participant(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
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

    async def async_step_remove_participant(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
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

    async def _add_participant(self, name: str, participant_config: dict[str, Any]) -> ConfigFlowResult:
        """Add a participant to the configuration."""
        new_data = self.config_entry.data.copy()
        new_participants = new_data["participants"].copy()
        new_participants[name] = participant_config
        new_data["participants"] = new_participants

        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)

        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        return self.async_create_entry(title="", data={})

    async def _update_participant(self, old_name: str, new_config: dict[str, Any]) -> ConfigFlowResult:
        """Update a participant in the configuration."""
        new_data = self.config_entry.data.copy()
        new_participants = new_data["participants"].copy()

        # Remove old participant and add updated one
        if old_name in new_participants:
            del new_participants[old_name]

        new_name = new_config.get("name_value", old_name)
        new_participants[new_name] = new_config

        new_data["participants"] = new_participants

        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)

        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
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
                ) -> ConfigFlowResult:
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
