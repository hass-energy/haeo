"""Generic reusable subentry flow for HAEO elements."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements import ElementConfigSchema
from custom_components.haeo.schema import flatten, schema_for_type, unflatten

_LOGGER = logging.getLogger(__name__)


class ElementSubentryFlow(ConfigSubentryFlow):
    """Generic reusable subentry flow for HAEO elements.

    Type parameter T should be the Schema TypedDict class for the element type.
    """

    def __init__(self, element_type: str, schema_cls: type[ElementConfigSchema], defaults: dict[str, Any]) -> None:
        """Initialize the element subentry flow.

        Args:
            element_type: Type of element (battery, grid, etc.)
            schema_cls: Schema class for this element type
            defaults: Default values for this element type

        """
        self.element_type: str = element_type
        self.schema_cls: type[ElementConfigSchema] = schema_cls
        self.defaults: dict[str, Any] = defaults

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Add new element - validates name uniqueness, creates subentry."""
        errors: dict[str, str] = {}

        hub_entry = self._get_entry()

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors[CONF_NAME] = "missing_name"
            # Check duplicate names in sibling subentries
            elif name in hub_entry.subentries.values():
                errors[CONF_NAME] = "name_exists"

            if not errors:
                # Store the configuration in home assistant
                return self.async_create_entry(
                    title=name, data=unflatten({CONF_ELEMENT_TYPE: self.element_type, **user_input})
                )

        # List of existing participant names
        participants = [entry.data["name"] for entry in hub_entry.subentries.values() if "name" in entry.data]
        schema = schema_for_type(
            self.schema_cls,
            defaults=flatten(self.defaults),
            participants=participants,
            current_element_name=None,
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Reconfigure existing element - similar to user but updates existing."""

        errors: dict[str, str] = {}
        hub_entry = self._get_entry()
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            new_name = user_input.get(CONF_NAME)
            if not new_name:
                errors[CONF_NAME] = "missing_name"

            if not errors:
                # Update subentry with new configuration
                return self.async_update_reload_and_abort(
                    hub_entry,
                    subentry,
                    title=str(new_name),
                    data=unflatten({**user_input, CONF_ELEMENT_TYPE: self.element_type}),
                )

        # Names of all other participants excluding this subentry
        participants = [
            entry.data["name"]
            for entry in hub_entry.subentries.values()
            if "name" in entry.data and entry.subentry_id != subentry.subentry_id
        ]
        schema = schema_for_type(
            self.schema_cls,
            defaults=flatten(self.defaults),
            participants=participants,
            current_element_name=subentry.data.get(CONF_NAME),
        )

        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)


def create_subentry_flow_class(
    element_type: str, schema_cls: type[ElementConfigSchema], defaults: dict[str, Any]
) -> type[ElementSubentryFlow]:
    """Create strongly-typed subentry flow class for element type."""

    class TypedElementSubentryFlow(ElementSubentryFlow):
        """Typed subentry flow for specific element type."""

        def __init__(self) -> None:
            """Initialize the typed flow."""
            super().__init__(element_type, schema_cls, defaults)

    TypedElementSubentryFlow.__name__ = f"{element_type.title().replace('_', '')}SubentryFlow"
    return TypedElementSubentryFlow
