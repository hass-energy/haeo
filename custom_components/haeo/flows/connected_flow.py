"""Shared flow for elements that connect to one other element and configure sectioned inputs.

A flow built on it declares its element type and its form sections. Pricing
fields the element type surfaces from policy rules show in the section their
hint names and are saved as policy rules rather than in the element's config.
"""

from collections.abc import Mapping
from typing import (
    Any,  # noqa: TID251  # HA flow signatures are Any-typed upstream
    ClassVar,
)

from homeassistant.config_entries import SubentryFlowResult
import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import (
    get_connection_target_name,
    is_connection_target,
    normalize_connection_target,
)
from custom_components.haeo.core.schema.field_hints import SurfacedPriceHint
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.core.schema.surfaced_policy import get_surfaced_price_hints
from custom_components.haeo.elements import get_input_field_schema_info, get_surfaced_input_fields
from custom_components.haeo.elements.input_fields import InputFieldGroups
from custom_components.haeo.flows.element_flow import ElementSubentryFlow, build_sectioned_inclusion_map
from custom_components.haeo.flows.entity_metadata import extract_entity_metadata
from custom_components.haeo.flows.field_schema import (
    SectionDefinition,
    as_mapping,
    as_str,
    build_sectioned_choose_defaults,
    build_sectioned_choose_schema,
    convert_sectioned_choose_data_to_config,
    preprocess_sectioned_choose_input,
    sectioned_view,
    validate_sectioned_choose_fields,
)
from custom_components.haeo.flows.surfaced_policy import (
    build_surfaced_defaults,
    build_surfaced_schema_entries,
    save_surfaced_rules_from_input,
)
from custom_components.haeo.sections import build_common_fields


def _stored_connection(subentry_data: Mapping[str, object] | None) -> str | None:
    """Return the name of the element a stored config connects to, or None for a new element."""
    connection = subentry_data.get(CONF_CONNECTION) if subentry_data else None
    return get_connection_target_name(connection) if is_connection_target(connection) else as_str(connection)


class ConnectedElementSubentryFlow(ElementSubentryFlow):
    """Flow for an element that connects to one other element and configures sectioned inputs."""

    # Placeholders the form's description reads
    description_placeholders: ClassVar[dict[str, str] | None] = None

    # The sections of the configuration form
    sections: ClassVar[tuple[SectionDefinition, ...]]

    def _surfaced_hints_by_section(self) -> dict[str, dict[str, SurfacedPriceHint]]:
        """Return the element type's surfaced pricing hints, grouped by the section they show in."""
        grouped: dict[str, dict[str, SurfacedPriceHint]] = {}
        for field_name, hint in get_surfaced_price_hints(self.element_type).items():
            grouped.setdefault(hint.section, {})[field_name] = hint
        return grouped

    def _surfaced_fields(self) -> tuple[str, ...]:
        """Return the surfaced pricing fields, which are saved as policy rules rather than in the config."""
        return tuple(get_surfaced_price_hints(self.element_type))

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle user step: name, connection, and input configuration."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step: name, connection, and input configuration."""
        return await self._async_step_user(user_input)

    async def _async_step_user(self, user_input: dict[str, object] | None) -> SubentryFlowResult:
        """Shared logic for user and reconfigure steps."""
        subentry = self._get_subentry()
        subentry_data: dict[str, object] | None = dict(subentry.data) if subentry else None
        participants = self._get_participant_names()
        current_connection = _stored_connection(subentry_data)
        default_name = await self._async_get_default_name()
        if current_connection is None:
            current_connection = participants[0] if participants else ""
        input_fields = self._get_input_fields()

        sections = self.sections
        user_input = preprocess_sectioned_choose_input(user_input, input_fields, sections)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            config = self._build_config(user_input)
            return await self._async_finalize(config, user_input)

        entity_metadata = extract_entity_metadata(self.hass, self._get_entry())
        section_inclusion_map = build_sectioned_inclusion_map(input_fields, entity_metadata)
        schema = self._build_schema(
            participants,
            input_fields,
            section_inclusion_map,
            current_connection,
            subentry_data,
        )
        defaults = (
            user_input
            if user_input is not None
            else self._build_defaults(
                default_name,
                input_fields,
                subentry_data,
                current_connection,
            )
        )
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders=self.description_placeholders,
        )

    def _build_schema(
        self,
        participants: list[str],
        input_fields: InputFieldGroups,
        section_inclusion_map: dict[str, dict[str, list[str]]],
        current_connection: str | None = None,
        subentry_data: Mapping[str, object] | None = None,
    ) -> vol.Schema:
        """Build the schema with name, connection, and choose selectors for inputs."""
        field_schema = get_input_field_schema_info(self.element_type, input_fields)
        surfaced_fields = get_surfaced_input_fields(self.element_type)
        element_name = as_str(subentry_data.get(CONF_NAME)) if subentry_data else None
        surfaced_entries = {
            section: build_surfaced_schema_entries(
                self.hass,
                self._get_entry(),
                element_name,
                hints,
                {field_name: surfaced_fields[field_name] for field_name in hints},
            )
            for section, hints in self._surfaced_hints_by_section().items()
        }
        return build_sectioned_choose_schema(
            self.sections,
            input_fields,
            field_schema,
            section_inclusion_map,
            current_data=sectioned_view(subentry_data),
            top_level_entries=build_common_fields(
                include_connection=True,
                participants=participants,
                current_connection=current_connection,
            ),
            extra_field_entries=surfaced_entries,
        )

    def _build_defaults(
        self,
        default_name: str,
        input_fields: InputFieldGroups,
        subentry_data: Mapping[str, object] | None = None,
        connection_default: str | None = None,
    ) -> dict[str, object]:
        """Build default values for the form."""
        surfaced_fields = get_surfaced_input_fields(self.element_type)
        element_name = as_str(subentry_data.get(CONF_NAME)) if subentry_data else None
        surfaced_defaults = {
            section: build_surfaced_defaults(
                self._get_entry(),
                element_name,
                hints,
                {field_name: surfaced_fields[field_name] for field_name in hints},
            )
            for section, hints in self._surfaced_hints_by_section().items()
        }
        return {
            CONF_NAME: default_name if subentry_data is None else subentry_data.get(CONF_NAME),
            CONF_CONNECTION: connection_default
            if connection_default is not None
            else _stored_connection(subentry_data),
            **build_sectioned_choose_defaults(
                self.sections,
                input_fields,
                current_data=subentry_data,
                base_defaults=surfaced_defaults,
            ),
        }

    def _validate_user_input(
        self,
        user_input: dict[str, object] | None,
        input_fields: InputFieldGroups,
    ) -> dict[str, str] | None:
        """Validate user input and return errors dict if any."""
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        self._validate_name(as_str(user_input.get(CONF_NAME)), errors)
        self._validate_endpoint(as_str(user_input.get(CONF_CONNECTION)), CONF_CONNECTION, errors)
        field_schema = get_input_field_schema_info(self.element_type, input_fields)
        errors.update(
            validate_sectioned_choose_fields(
                user_input,
                input_fields,
                field_schema,
                self.sections,
                exclude_fields=self._surfaced_fields(),
            )
        )
        return errors if errors else None

    def _build_config(self, user_input: Mapping[str, object]) -> dict[str, object]:
        """Build final config dict from user input."""
        config_dict = convert_sectioned_choose_data_to_config(
            user_input,
            self._get_input_fields(),
            self.sections,
            exclude_fields=self._surfaced_fields(),
        )
        return {
            CONF_ELEMENT_TYPE: self.element_type,
            CONF_NAME: user_input[CONF_NAME],
            CONF_CONNECTION: normalize_connection_target(user_input[CONF_CONNECTION]),
            **config_dict,
        }

    async def _async_finalize(self, config: dict[str, object], user_input: Mapping[str, object]) -> SubentryFlowResult:
        """Save the surfaced pricing fields as policy rules, then create or update the entry."""
        name = str(user_input[CONF_NAME])
        is_new = self._get_subentry() is None
        for section, hints in self._surfaced_hints_by_section().items():
            save_surfaced_rules_from_input(
                self.hass,
                self._get_entry(),
                name,
                as_mapping(user_input.get(section)),
                hints,
                {field_name: f"{name} {field_name.replace('_', ' ')}" for field_name in hints},
                apply_defaults=is_new,
            )
        return await self._async_save_entry(name, config)


__all__ = ["ConnectedElementSubentryFlow"]
