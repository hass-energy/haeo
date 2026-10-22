"""Shared flow for elements configured through a form of sections of choose inputs.

A flow built on it declares its element type and its form sections, and
overrides the hooks for any fields beyond its name and its sectioned inputs.
Pricing fields the element type surfaces from policy rules show in the section
that lists them and are saved as policy rules rather than in the element's config.
"""

from collections.abc import Mapping
from typing import (
    Any,  # noqa: TID251  # HA flow signatures upstream; voluptuous schema value types are heterogeneous by design
    ClassVar,
)

from homeassistant.config_entries import SubentryFlowResult
import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.data.loader.extractors import EntityMetadata
from custom_components.haeo.core.schema.field_hints import SurfacedPriceHint
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
from custom_components.haeo.flows.sections import build_common_fields
from custom_components.haeo.flows.surfaced_policy import (
    build_surfaced_defaults,
    build_surfaced_schema_entries,
    save_surfaced_rules_from_input,
)

type FieldEntries = dict[str, tuple[vol.Marker, object]]


class SectionedElementSubentryFlow(ElementSubentryFlow):
    """Flow for an element configured through a form of sections of choose inputs."""

    # The sections of the configuration form
    sections: ClassVar[tuple[SectionDefinition, ...]]

    # Placeholders the form's description reads
    description_placeholders: ClassVar[dict[str, str] | None] = None

    # --- Hooks for fields beyond the name and the sectioned inputs ---

    def _top_level_entries(self, subentry_data: Mapping[str, object] | None) -> FieldEntries:
        """Return the form fields shown above the sections."""
        _ = subentry_data
        return build_common_fields(include_connection=False)

    def _top_level_defaults(self, subentry_data: Mapping[str, object] | None) -> dict[str, object]:
        """Return the defaults of the top-level fields other than the name."""
        _ = subentry_data
        return {}

    def _section_entries(
        self, subentry_data: Mapping[str, object] | None, entity_metadata: list[EntityMetadata]
    ) -> dict[str, FieldEntries]:
        """Return form fields added to sections beyond their choose inputs, keyed by section."""
        surfaced_fields = get_surfaced_input_fields(self.element_type)
        element_name = as_str(subentry_data.get(CONF_NAME)) if subentry_data else None
        return {
            section: dict(
                build_surfaced_schema_entries(
                    self.hass,
                    self._get_entry(),
                    element_name,
                    hints,
                    {field_name: surfaced_fields[field_name] for field_name in hints},
                    entity_metadata,
                )
            )
            for section, hints in self._surfaced_hints_by_section().items()
        }

    def _section_defaults(self, subentry_data: Mapping[str, object] | None) -> dict[str, dict[str, object]]:
        """Return defaults of the fields added to sections, keyed by section."""
        surfaced_fields = get_surfaced_input_fields(self.element_type)
        element_name = as_str(subentry_data.get(CONF_NAME)) if subentry_data else None
        return {
            section: build_surfaced_defaults(
                self._get_entry(),
                element_name,
                hints,
                {field_name: surfaced_fields[field_name] for field_name in hints},
            )
            for section, hints in self._surfaced_hints_by_section().items()
        }

    def _validate_fields(self, user_input: Mapping[str, object], errors: dict[str, str]) -> None:
        """Add errors for fields beyond the name and the sectioned inputs."""
        _ = (user_input, errors)

    def _config_fields(
        self, user_input: Mapping[str, object], sections: Mapping[str, Mapping[str, object]]
    ) -> dict[str, object]:
        """Return config fields beyond the type, name and converted sections, which they override."""
        _ = (user_input, sections)
        return {}

    # --- Surfaced policy pricing ---

    def _surfaced_hints_by_section(self) -> dict[str, dict[str, SurfacedPriceHint]]:
        """Return the element type's surfaced pricing hints, grouped by the form section listing them."""
        grouped: dict[str, dict[str, SurfacedPriceHint]] = {}
        for field_name, hint in get_surfaced_price_hints(self.element_type).items():
            section = next(section.key for section in self.sections if field_name in section.fields)
            grouped.setdefault(section, {})[field_name] = hint
        return grouped

    def _surfaced_fields(self) -> tuple[str, ...]:
        """Return the surfaced pricing fields, which are saved as policy rules rather than in the config."""
        return tuple(get_surfaced_price_hints(self.element_type))

    # --- Steps ---

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle the user step: name and input configuration."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle the reconfigure step: name and input configuration."""
        return await self._async_step_user(user_input)

    async def _async_step_user(self, user_input: dict[str, object] | None) -> SubentryFlowResult:
        """Shared logic for user and reconfigure steps."""
        subentry = self._get_subentry()
        subentry_data: dict[str, object] | None = dict(subentry.data) if subentry else None
        input_fields = self._get_input_fields()
        user_input = preprocess_sectioned_choose_input(user_input, input_fields, self.sections)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            return await self._async_finalize(self._build_config(user_input), user_input)

        schema = self._build_schema(input_fields, extract_entity_metadata(self.hass, self._get_entry()), subentry_data)
        defaults = (
            user_input
            if user_input is not None
            else self._build_defaults(await self._async_get_default_name(), input_fields, subentry_data)
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, defaults),
            errors=errors,
            description_placeholders=self.description_placeholders,
        )

    def _build_schema(
        self,
        input_fields: InputFieldGroups,
        entity_metadata: list[EntityMetadata],
        subentry_data: Mapping[str, object] | None = None,
    ) -> vol.Schema:
        """Build the form schema: top-level fields, then choose selectors for the sectioned inputs."""
        return build_sectioned_choose_schema(
            self.sections,
            input_fields,
            get_input_field_schema_info(self.element_type, input_fields),
            build_sectioned_inclusion_map(input_fields, entity_metadata),
            current_data=sectioned_view(subentry_data),
            top_level_entries=self._top_level_entries(subentry_data),
            extra_field_entries=self._section_entries(subentry_data, entity_metadata),
        )

    def _build_defaults(
        self,
        default_name: str,
        input_fields: InputFieldGroups,
        subentry_data: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        """Build default values for the form."""
        return {
            CONF_NAME: default_name if subentry_data is None else subentry_data.get(CONF_NAME),
            **self._top_level_defaults(subentry_data),
            **build_sectioned_choose_defaults(
                self.sections,
                input_fields,
                current_data=subentry_data,
                base_defaults=self._section_defaults(subentry_data),
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
        self._validate_fields(user_input, errors)
        errors.update(
            validate_sectioned_choose_fields(
                user_input,
                input_fields,
                get_input_field_schema_info(self.element_type, input_fields),
                self.sections,
                exclude_fields=self._surfaced_fields(),
            )
        )
        return errors if errors else None

    def _build_config(self, user_input: Mapping[str, object]) -> dict[str, object]:
        """Build final config dict from user input."""
        sections = convert_sectioned_choose_data_to_config(
            user_input,
            self._get_input_fields(),
            self.sections,
            exclude_fields=self._surfaced_fields(),
        )
        return {
            CONF_ELEMENT_TYPE: self.element_type,
            CONF_NAME: user_input[CONF_NAME],
            **sections,
            **self._config_fields(user_input, sections),
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


__all__ = ["FieldEntries", "SectionedElementSubentryFlow"]
