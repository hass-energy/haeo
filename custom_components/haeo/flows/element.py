"""Generic reusable subentry flow for HAEO elements."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult

from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.schema import schema_for_type
from custom_components.haeo.types import ElementConfigSchema

_LOGGER = logging.getLogger(__name__)


class ElementSubentryFlow[T: type[ElementConfigSchema]](ConfigSubentryFlow):
    """Generic reusable subentry flow for HAEO elements.

    Type parameter T should be the Schema TypedDict class for the element type.
    """

    def __init__(self, element_type: str, schema_cls: T, defaults: dict[str, Any]) -> None:
        """Initialize the element subentry flow.

        Args:
            element_type: Type of element (battery, grid, etc.)
            schema_cls: Schema class for this element type
            defaults: Default values for this element type

        """
        self.element_type: str = element_type
        self.schema_cls: T = schema_cls
        self.defaults: dict[str, Any] = defaults

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Add new element - validates name uniqueness, creates subentry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get("name_value")
            if not name:
                errors["name_value"] = "missing_name"
            else:
                # Check duplicate names in sibling subentries
                hub_entry = self._get_entry()
                for subentry in hub_entry.subentries.values():
                    if subentry.data.get("name_value") == name:
                        errors["name_value"] = "name_exists"
                        break

            if not errors:
                # Subentries don't store parent_entry_id in their data
                # The parent relationship is managed by Home Assistant
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_ELEMENT_TYPE: self.element_type,
                        **user_input,
                    },
                )

        # Build schema with context
        # Get current hub entry for validation
        hub_entry = self._get_entry()

        # Check for duplicate names
        participants = self._get_participant_entries(hub_entry.entry_id)
        flattened_defaults = {f"{k}_value": v for k, v in self.defaults.items()}
        # Convert participants dict keys to list of strings for ElementNameFieldMeta
        participants_list = list(participants.keys())
        schema = schema_for_type(
            self.schema_cls,
            defaults=flattened_defaults,
            participants=participants_list,
            current_element_name=None,
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Reconfigure existing element - similar to user but updates existing."""
        subentry = self._get_reconfigure_subentry()
        current_name = subentry.data.get("name_value")
        errors: dict[str, str] = {}

        if user_input is not None:
            new_name = user_input.get("name_value")
            if not new_name:
                errors["name_value"] = "missing_name"
            elif new_name != current_name:
                # Check duplicate names in sibling subentries (excluding current)
                hub_entry = self._get_entry()
                for other_subentry in hub_entry.subentries.values():
                    if (
                        other_subentry.subentry_id != subentry.subentry_id
                        and other_subentry.data.get("name_value") == new_name
                    ):
                        errors["name_value"] = "name_exists"
                        break

            if not errors:
                # Update subentry with new configuration
                hub_entry = self._get_entry()
                new_title = user_input.get("name_value", current_name) or current_name
                return self.async_update_reload_and_abort(
                    hub_entry,
                    subentry,
                    title=str(new_title),
                    data={
                        CONF_ELEMENT_TYPE: self.element_type,
                        **user_input,
                    },
                )

        # Build schema with context
        hub_entry = self._get_entry()
        participants = self._get_participant_entries(
            hub_entry.entry_id,
            exclude_subentry_id=subentry.subentry_id,
        )
        # Use current entry data as defaults - keys are already in correct schema format
        flattened_defaults = {k: v for k, v in subentry.data.items() if k != CONF_ELEMENT_TYPE}
        # Convert participants dict keys to list of strings for ElementNameFieldMeta
        participants_list = list(participants.keys())
        schema = schema_for_type(
            self.schema_cls,
            defaults=flattened_defaults,
            participants=participants_list,
            current_element_name=current_name,
        )

        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)

    def _get_participant_entries(
        self, hub_entry_id: str, exclude_subentry_id: str | None = None
    ) -> dict[str, dict[str, Any]]:
        """Get all participant entries for the hub.

        Args:
            hub_entry_id: Entry ID of the parent hub
            exclude_subentry_id: Subentry ID to exclude (for reconfigure flow)

        Returns:
            Dictionary mapping element names to their configurations

        """
        participants: dict[str, dict[str, Any]] = {}
        _LOGGER.debug("Getting participants from hub subentries for hub=%s", hub_entry_id)

        hub_entry = self.hass.config_entries.async_get_entry(hub_entry_id)
        if not hub_entry:
            _LOGGER.warning("Hub entry %s not found", hub_entry_id)
            return participants

        _LOGGER.debug("Hub has %d subentries", len(hub_entry.subentries))

        for subentry in hub_entry.subentries.values():
            # Skip if this is the excluded subentry (for reconfigure flow)
            if exclude_subentry_id and subentry.subentry_id == exclude_subentry_id:
                _LOGGER.debug("Excluding subentry %s (reconfigure)", subentry.subentry_id)
                continue

            # Skip network subentry (not a participant that can be a connection endpoint)
            if subentry.subentry_type == "network":
                _LOGGER.debug("Skipping network subentry")
                continue

            # Skip connection subentries (connections can't be connection endpoints)
            if subentry.subentry_type == "connection":
                _LOGGER.debug("Skipping connection subentry: %s", subentry.data.get("name_value"))
                continue

            name = subentry.data.get("name_value")
            if name:
                # Convert subentry data to participant config format
                participant_config = {
                    CONF_ELEMENT_TYPE: subentry.subentry_type,
                    **subentry.data,
                }
                participants[name] = participant_config
                _LOGGER.debug(
                    "Added participant: %s (type=%s, id=%s)",
                    name,
                    subentry.subentry_type,
                    subentry.subentry_id,
                )
            else:
                _LOGGER.warning("Subentry %s has no name_value", subentry.subentry_id)

        _LOGGER.debug("Found %d participants: %s", len(participants), list(participants.keys()))
        return participants


def create_subentry_flow_class(
    element_type: str, schema_cls: type[ElementConfigSchema], defaults: dict[str, Any]
) -> type[ElementSubentryFlow[type[ElementConfigSchema]]]:
    """Create strongly-typed subentry flow class for element type.

    Args:
        element_type: Type of element (battery, grid, etc.)
        schema_cls: Schema class for this element type
        defaults: Default values for this element type

    Returns:
        A configured ElementSubentryFlow subclass for the element type

    """

    class TypedElementSubentryFlow(ElementSubentryFlow[type[ElementConfigSchema]]):
        """Typed subentry flow for specific element type."""

        def __init__(self) -> None:
            """Initialize the typed flow."""
            super().__init__(element_type, schema_cls, defaults)

    TypedElementSubentryFlow.__name__ = f"{element_type.title().replace('_', '')}SubentryFlow"
    return TypedElementSubentryFlow
