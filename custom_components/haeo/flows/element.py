"""Generic reusable subentry flow for HAEO elements."""

from typing import Any, cast

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.translation import async_get_translations

from custom_components.haeo.const import CONF_ADVANCED_MODE, CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN, URL_HAFO
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.elements import (
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPE_LOAD,
    ELEMENT_TYPE_NODE,
    ELEMENT_TYPES,
    ConnectivityLevel,
    ElementConfigSchema,
    is_element_config_schema,
)
from custom_components.haeo.network import evaluate_network_connectivity
from custom_components.haeo.schema import schema_for_type
from custom_components.haeo.validation import collect_participant_configs


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
        super().__init__()
        self.element_type: str = element_type
        self.schema_cls: type[ElementConfigSchema] = schema_cls
        self.defaults: dict[str, Any] = defaults

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Add new element - validates name uniqueness, creates subentry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors[CONF_NAME] = "missing_name"
            # Check duplicate names in sibling subentries
            elif name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            if not errors:
                # user_input has been validated by voluptuous via the schema
                # Cast is safe here as we're just adding the element_type field
                new_config = cast("ElementConfigSchema", {CONF_ELEMENT_TYPE: self.element_type, **user_input})

                hub_entry = self._get_entry()
                participant_configs = collect_participant_configs(hub_entry)
                participant_configs[new_config[CONF_NAME]] = new_config
                await evaluate_network_connectivity(self.hass, hub_entry, participant_configs=participant_configs)

                return self.async_create_entry(title=name, data=new_config)

        # Default names for element types which are likely to have a single instance
        suggested_values = self.defaults
        if self.element_type not in [ELEMENT_TYPE_CONNECTION, ELEMENT_TYPE_NODE]:
            translations = await async_get_translations(
                self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
            )
            default_name = translations.get(f"component.{DOMAIN}.config_subentries.{self.element_type}.flow_title", "")
            suggested_values = {CONF_NAME: default_name, **self.defaults}

        # Show the form to the user
        schema = schema_for_type(
            self.schema_cls,
            entity_metadata=extract_entity_metadata(self.hass),
            participants=self._get_non_connection_element_names(),
            current_element_name=None,
        )
        schema = self.add_suggested_values_to_schema(schema, suggested_values)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders=self._get_description_placeholders(),
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Reconfigure existing element - similar to user but updates existing."""

        errors: dict[str, str] = {}
        hub_entry = self._get_entry()
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            new_name = user_input.get(CONF_NAME)
            if not new_name:
                errors[CONF_NAME] = "missing_name"
            elif new_name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            if not errors:
                # user_input has been validated by voluptuous via the schema
                # Cast is safe here as we're just adding the element_type field
                updated_config = cast("ElementConfigSchema", {**user_input, CONF_ELEMENT_TYPE: self.element_type})

                participant_configs = collect_participant_configs(hub_entry)
                current_name = subentry.data.get(CONF_NAME)
                if isinstance(current_name, str):
                    participant_configs.pop(current_name, None)
                participant_configs[updated_config[CONF_NAME]] = updated_config
                await evaluate_network_connectivity(self.hass, hub_entry, participant_configs=participant_configs)

                return self.async_update_and_abort(
                    hub_entry,
                    subentry,
                    title=str(new_name),
                    data=updated_config,
                )

        # Get the schema
        schema = schema_for_type(
            self.schema_cls,
            entity_metadata=extract_entity_metadata(self.hass),
            participants=self._get_non_connection_element_names(),
            current_element_name=subentry.data.get(CONF_NAME),
        )
        schema = self.add_suggested_values_to_schema(schema, subentry.data)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
            description_placeholders=self._get_description_placeholders(),
        )

    def _get_used_names(self) -> set[str]:
        """Return all configured element names excluding the current subentry when present."""
        return {
            subentry.title
            for subentry in self._get_entry().subentries.values()
            if subentry.subentry_id != self._get_current_subentry_id()
        }

    def _get_non_connection_element_names(self) -> list[str]:
        """Return participant names available for connection endpoints excluding the current subentry.

        Filters elements based on their connectivity level:
        - ALWAYS: Always included
        - ADVANCED: Only included when advanced mode is enabled
        - NEVER: Never included (e.g., connections)
        """
        hub_entry = self._get_entry()
        advanced_mode = hub_entry.data.get(CONF_ADVANCED_MODE, False)

        result: list[str] = []
        for name, config in self._get_other_element_entries().items():
            connectivity = ELEMENT_TYPES[config[CONF_ELEMENT_TYPE]].connectivity

            if connectivity == ConnectivityLevel.ALWAYS or (
                connectivity == ConnectivityLevel.ADVANCED and advanced_mode
            ):
                result.append(name)

        return result

    def _get_other_element_entries(self) -> dict[str, ElementConfigSchema]:
        """Return other subentries which are Element participants."""
        hub = self._get_entry()
        current = self._get_current_subentry_id()

        return {
            subentry.title: subentry.data
            for subentry in hub.subentries.values()
            if subentry.subentry_id != current and is_element_config_schema(subentry.data)
        }

    def _get_current_subentry_id(self) -> str | None:
        """Return the active subentry ID when reconfiguring, otherwise None."""
        try:
            return self._get_reconfigure_subentry().subentry_id
        except Exception:
            return None

    def _get_description_placeholders(self) -> dict[str, str] | None:
        """Return description placeholders for the current element type."""
        if self.element_type == ELEMENT_TYPE_LOAD:
            return {"hafo_url": URL_HAFO}
        return None


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
