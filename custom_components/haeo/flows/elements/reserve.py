"""Reserve element configuration flows."""

from collections.abc import Callable, Mapping
from typing import Any  # noqa: TID251  # HA flow signatures are Any-typed upstream

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode
import voluptuous as vol

from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES, ElementAdapter, is_element_type
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.reserve import (
    CONF_GENERATION,
    CONF_LOADS,
    CONF_MINIMUM,
    CONF_SHORTFALL_COST,
    CONF_STORAGE,
    CONF_WINDOW,
    ELEMENT_TYPE,
    SECTION_PARTICIPANTS,
    SECTION_PRICING,
    SECTION_REQUIREMENT,
)
from custom_components.haeo.elements import get_input_field_schema_info
from custom_components.haeo.elements.input_fields import InputFieldGroups
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_sectioned_inclusion_map
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

# Which elements each participant list offers, by what the element's adapter can do
PARTICIPANT_FILTERS: dict[str, Callable[[ElementType, ElementAdapter], bool]] = {
    CONF_LOADS: lambda _element_type, adapter: adapter.can_sink and not adapter.can_source,
    CONF_GENERATION: lambda _element_type, adapter: adapter.can_source and not adapter.can_sink,
    CONF_STORAGE: lambda element_type, _adapter: element_type == ElementType.BATTERY,
}


class ReserveSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle reserve element configuration flows."""

    def _get_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the configuration step."""
        return (
            SectionDefinition(key=SECTION_PARTICIPANTS, fields=(CONF_LOADS, CONF_GENERATION, CONF_STORAGE)),
            SectionDefinition(key=SECTION_REQUIREMENT, fields=(CONF_WINDOW, CONF_MINIMUM)),
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
        input_fields = self._get_input_fields(ELEMENT_TYPE)
        sections = self._get_sections()
        user_input = preprocess_sectioned_choose_input(user_input, input_fields, sections)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            config = self._build_config(user_input)
            name = str(user_input[CONF_NAME])
            if subentry is not None:
                return self.async_update_and_abort(self._get_entry(), subentry, title=name, data=config)
            return self.async_create_entry(title=name, data=config)

        entity_metadata = extract_entity_metadata(self.hass, self._get_entry())
        schema = build_sectioned_choose_schema(
            sections,
            input_fields,
            get_input_field_schema_info(ELEMENT_TYPE, input_fields),
            build_sectioned_inclusion_map(input_fields, entity_metadata),
            current_data=sectioned_view(subentry_data),
            top_level_entries={CONF_NAME: (vol.Required(CONF_NAME), str)},
            extra_field_entries={
                SECTION_PARTICIPANTS: {
                    field: (vol.Optional(field), self._participant_selector(field)) for field in PARTICIPANT_FILTERS
                }
            },
        )
        defaults = user_input if user_input is not None else await self._build_defaults(input_fields, subentry_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    def _participant_selector(self, field: str) -> SelectSelector:  # type: ignore[type-arg]
        """Build a multi-select of the elements a participant list offers."""
        offered = PARTICIPANT_FILTERS[field]
        current_id = self._get_current_subentry_id()
        options = [
            subentry.title
            for subentry in self._get_entry().subentries.values()
            if subentry.subentry_id != current_id
            and is_element_type(subentry.subentry_type)
            and offered(subentry.subentry_type, ELEMENT_TYPES[subentry.subentry_type])
        ]
        return SelectSelector(SelectSelectorConfig(options=options, multiple=True, mode=SelectSelectorMode.DROPDOWN))

    async def _build_defaults(
        self,
        input_fields: InputFieldGroups,
        subentry_data: Mapping[str, object] | None,
    ) -> dict[str, object]:
        """Build default values for the form."""
        participants = as_mapping(subentry_data.get(SECTION_PARTICIPANTS)) if subentry_data else {}
        participant_defaults = {field: participants.get(field, []) for field in PARTICIPANT_FILTERS}
        return {
            CONF_NAME: (
                subentry_data.get(CONF_NAME) if subentry_data else await self._async_get_default_name(ELEMENT_TYPE)
            ),
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
            errors["base"] = "reserve_storage_required"
        errors.update(
            validate_sectioned_choose_fields(
                user_input,
                input_fields,
                get_input_field_schema_info(ELEMENT_TYPE, input_fields),
                self._get_sections(),
            )
        )
        return errors if errors else None

    def _build_config(self, user_input: Mapping[str, object]) -> dict[str, object]:
        """Build final config dict from user input."""
        config = convert_sectioned_choose_data_to_config(
            user_input,
            self._get_input_fields(ELEMENT_TYPE),
            self._get_sections(),
        )
        config[SECTION_PARTICIPANTS] = {
            field: list(values)
            for field in PARTICIPANT_FILTERS
            if isinstance(values := as_mapping(user_input.get(SECTION_PARTICIPANTS)).get(field), list) and values
        }
        return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, CONF_NAME: user_input[CONF_NAME], **config}
