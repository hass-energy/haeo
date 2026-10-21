"""Buffer element configuration flow."""

from collections.abc import Mapping
from typing import Any  # noqa: TID251  # HA flow signatures are Any-typed upstream

from homeassistant.config_entries import SubentryFlowResult
from homeassistant.helpers.selector import Selector, SelectSelector, SelectSelectorConfig, SelectSelectorMode
import voluptuous as vol

from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES, is_element_type
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.buffer import (
    BUFFER_KINDS,
    BUFFER_ROLES,
    CONF_GENERATION,
    CONF_KIND,
    CONF_LEVEL,
    CONF_LOADS,
    CONF_SHORTFALL_COST,
    CONF_STORAGE,
    CONF_WINDOW,
    KIND_RESERVE,
    SECTION_PARTICIPANTS,
    SECTION_PRICING,
    SECTION_REQUIREMENT,
    BufferRole,
)
from custom_components.haeo.elements import get_input_field_schema_info
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


class BufferSubentryFlowHandler(ElementSubentryFlow):
    """Handle buffer element configuration flows."""

    element_type = ElementType.BUFFER

    def _get_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the configuration step."""
        return (
            SectionDefinition(key=SECTION_PARTICIPANTS, fields=(CONF_LOADS, CONF_GENERATION, CONF_STORAGE)),
            SectionDefinition(key=SECTION_REQUIREMENT, fields=(CONF_WINDOW, CONF_LEVEL)),
            SectionDefinition(key=SECTION_PRICING, fields=(CONF_SHORTFALL_COST,)),
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle user step: name, participants, and input configuration."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step: name, participants, and input configuration."""
        return await self._async_step_user(user_input)

    async def _async_step_user(self, user_input: dict[str, object] | None) -> SubentryFlowResult:
        """Shared logic for user and reconfigure steps."""
        subentry = self._get_subentry()
        subentry_data: dict[str, object] | None = dict(subentry.data) if subentry else None
        input_fields = self._get_input_fields()
        sections = self._get_sections()
        user_input = preprocess_sectioned_choose_input(user_input, input_fields, sections)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            config = self._build_config(user_input)
            name = str(user_input[CONF_NAME])
            return await self._async_save_entry(name, config)

        entity_metadata = extract_entity_metadata(self.hass, self._get_entry())
        schema = build_sectioned_choose_schema(
            sections,
            input_fields,
            get_input_field_schema_info(self.element_type, input_fields),
            build_sectioned_inclusion_map(input_fields, entity_metadata),
            current_data=sectioned_view(subentry_data),
            top_level_entries={
                CONF_NAME: (vol.Required(CONF_NAME), str),
                CONF_KIND: (
                    vol.Required(CONF_KIND),
                    SelectSelector(
                        SelectSelectorConfig(
                            options=list(BUFFER_KINDS), mode=SelectSelectorMode.LIST, translation_key="buffer_kind"
                        )
                    ),
                ),
            },
            extra_field_entries={
                SECTION_PARTICIPANTS: {
                    field: (vol.Optional(field), self._participant_selector(field)) for field in BUFFER_ROLES
                }
            },
        )
        defaults = user_input if user_input is not None else await self._build_defaults(input_fields, subentry_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    def _participant_selector(self, field: BufferRole) -> Selector[SelectSelectorConfig]:
        """Build a multi-select of the elements that can take a participant list's role."""
        current_id = self._get_current_subentry_id()
        options = [
            subentry.title
            for subentry in self._get_entry().subentries.values()
            if subentry.subentry_id != current_id
            and is_element_type(subentry.subentry_type)
            and field in ELEMENT_TYPES[subentry.subentry_type].buffer_roles
        ]
        return SelectSelector(SelectSelectorConfig(options=options, multiple=True, mode=SelectSelectorMode.DROPDOWN))

    async def _build_defaults(
        self,
        input_fields: InputFieldGroups,
        subentry_data: Mapping[str, object] | None,
    ) -> dict[str, object]:
        """Build default values for the form."""
        participants = as_mapping(subentry_data.get(SECTION_PARTICIPANTS)) if subentry_data else {}
        participant_defaults = {field: participants.get(field, []) for field in BUFFER_ROLES}
        return {
            CONF_NAME: (subentry_data.get(CONF_NAME) if subentry_data else await self._async_get_default_name()),
            CONF_KIND: subentry_data.get(CONF_KIND) if subentry_data else KIND_RESERVE,
            **build_sectioned_choose_defaults(
                self._get_sections(),
                input_fields,
                current_data=subentry_data,
                base_defaults={SECTION_PARTICIPANTS: participant_defaults},
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
        if not as_mapping(user_input.get(SECTION_PARTICIPANTS)).get(CONF_STORAGE):
            errors["base"] = "buffer_storage_required"
        errors.update(
            validate_sectioned_choose_fields(
                user_input,
                input_fields,
                get_input_field_schema_info(self.element_type, input_fields),
                self._get_sections(),
            )
        )
        return errors if errors else None

    def _build_config(self, user_input: Mapping[str, object]) -> dict[str, object]:
        """Build final config dict from user input."""
        config = convert_sectioned_choose_data_to_config(
            user_input,
            self._get_input_fields(),
            self._get_sections(),
        )
        config[SECTION_PARTICIPANTS] = {
            field: list(values)
            for field in BUFFER_ROLES
            if isinstance(values := as_mapping(user_input.get(SECTION_PARTICIPANTS)).get(field), list) and values
        }
        return {
            CONF_ELEMENT_TYPE: self.element_type,
            CONF_NAME: user_input[CONF_NAME],
            CONF_KIND: user_input[CONF_KIND],
            **config,
        }
