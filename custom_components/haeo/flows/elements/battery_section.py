"""Battery section element configuration flows."""

from typing import Any

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.elements import get_input_field_schema_info
from custom_components.haeo.elements.battery_section.adapter import adapter
from custom_components.haeo.elements.input_fields import InputFieldGroups
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_sectioned_inclusion_map
from custom_components.haeo.flows.field_schema import (
    SectionDefinition,
    build_sectioned_choose_defaults,
    build_sectioned_choose_schema,
    convert_sectioned_choose_data_to_config,
    preprocess_sectioned_choose_input,
    validate_sectioned_choose_fields,
)
from custom_components.haeo.schema.elements.battery_section import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    ELEMENT_TYPE,
    SECTION_STORAGE,
)
from custom_components.haeo.sections import SECTION_COMMON, build_common_fields, common_section


class BatterySectionSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle battery section element configuration flows."""

    def _get_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the configuration step."""
        return (
            common_section((CONF_NAME,), collapsed=False),
            SectionDefinition(key=SECTION_STORAGE, fields=(CONF_CAPACITY, CONF_INITIAL_CHARGE), collapsed=False),
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle user step: name and input configuration."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step: name and input configuration."""
        return await self._async_step_user(user_input)

    async def _async_step_user(self, user_input: dict[str, Any] | None) -> SubentryFlowResult:
        """Shared logic for user and reconfigure steps."""
        subentry = self._get_subentry()
        subentry_data = dict(subentry.data) if subentry else None
        default_name = await self._async_get_default_name(ELEMENT_TYPE)
        input_fields = adapter.inputs(subentry_data)

        sections = self._get_sections()
        user_input = preprocess_sectioned_choose_input(user_input, input_fields, sections)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            config = self._build_config(user_input)
            return self._finalize(config, user_input)

        entity_metadata = extract_entity_metadata(self.hass)
        section_inclusion_map = build_sectioned_inclusion_map(input_fields, entity_metadata)

        schema = self._build_schema(
            input_fields,
            section_inclusion_map,
            subentry_data,
        )
        defaults = (
            user_input if user_input is not None else self._build_defaults(default_name, input_fields, subentry_data)
        )
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    def _build_schema(
        self,
        input_fields: InputFieldGroups,
        section_inclusion_map: dict[str, dict[str, list[str]]],
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema with name and choose selectors for inputs."""
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        sections = self._get_sections()
        return build_sectioned_choose_schema(
            sections,
            input_fields,
            field_schema,
            section_inclusion_map,
            current_data=subentry_data,
            extra_field_entries={
                SECTION_COMMON: build_common_fields(include_connection=False),
            },
        )

    def _build_defaults(
        self,
        default_name: str,
        input_fields: InputFieldGroups,
        subentry_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build default values for the form."""
        common_data = subentry_data.get(SECTION_COMMON, {}) if subentry_data else {}
        return build_sectioned_choose_defaults(
            self._get_sections(),
            input_fields,
            current_data=subentry_data,
            base_defaults={
                SECTION_COMMON: {
                    CONF_NAME: default_name if subentry_data is None else common_data.get(CONF_NAME),
                }
            },
        )

    def _validate_user_input(
        self,
        user_input: dict[str, Any] | None,
        input_fields: InputFieldGroups,
    ) -> dict[str, str] | None:
        """Validate user input and return errors dict if any."""
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        common_input = user_input.get(SECTION_COMMON, {})
        self._validate_name(common_input.get(CONF_NAME), errors)
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        errors.update(
            validate_sectioned_choose_fields(
                user_input,
                input_fields,
                field_schema,
                self._get_sections(),
            )
        )
        return errors if errors else None

    def _build_config(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Build final config dict from user input."""
        input_fields = adapter.inputs(user_input)
        config_dict = convert_sectioned_choose_data_to_config(
            user_input,
            input_fields,
            self._get_sections(),
        )

        return {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE,
            **config_dict,
        }

    def _finalize(self, config: dict[str, Any], user_input: dict[str, Any]) -> SubentryFlowResult:
        """Finalize the flow by creating or updating the entry."""
        name = str(user_input.get(SECTION_COMMON, {}).get(CONF_NAME))
        subentry = self._get_subentry()
        if subentry is not None:
            return self.async_update_and_abort(self._get_entry(), subentry, title=name, data=config)
        return self.async_create_entry(title=name, data=config)
