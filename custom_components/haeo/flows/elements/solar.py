"""Solar element configuration flows."""

from typing import Any

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
import voluptuous as vol

from custom_components.haeo.adapters.elements.solar import adapter
from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.elements import get_input_field_schema_info
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
from custom_components.haeo.schema import get_connection_target_name, normalize_connection_target
from custom_components.haeo.schema.elements import ElementType
from custom_components.haeo.schema.elements.solar import CONF_CURTAILMENT, SECTION_CURTAILMENT
from custom_components.haeo.sections import (
    CONF_CONNECTION,
    CONF_FORECAST,
    CONF_PRICE_SOURCE_TARGET,
    SECTION_COMMON,
    build_common_fields,
    common_section,
    forecast_section,
    pricing_section,
)


class SolarSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle solar element configuration flows."""

    def _get_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the configuration step."""
        return (
            common_section((CONF_NAME, CONF_CONNECTION), collapsed=False),
            forecast_section((CONF_FORECAST,), collapsed=False),
            pricing_section((CONF_PRICE_SOURCE_TARGET,), collapsed=False),
            SectionDefinition(key=SECTION_CURTAILMENT, fields=(CONF_CURTAILMENT,), collapsed=True),
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle user step: name, connection, and input configuration."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step: name, connection, and input configuration."""
        return await self._async_step_user(user_input)

    async def _async_step_user(self, user_input: dict[str, Any] | None) -> SubentryFlowResult:
        """Shared logic for user and reconfigure steps."""
        subentry = self._get_subentry()
        subentry_data = dict(subentry.data) if subentry else None
        participants = self._get_participant_names()
        current_connection = (
            get_connection_target_name(subentry_data.get(SECTION_COMMON, {}).get(CONF_CONNECTION))
            if subentry_data
            else None
        )
        default_name = await self._async_get_default_name(ElementType.SOLAR)
        if not isinstance(current_connection, str):
            current_connection = participants[0] if participants else ""
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

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    def _build_schema(
        self,
        participants: list[str],
        input_fields: InputFieldGroups,
        section_inclusion_map: dict[str, dict[str, list[str]]],
        current_connection: str | None = None,
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema with name, connection, and choose selectors for inputs."""
        field_schema = get_input_field_schema_info(ElementType.SOLAR, input_fields)
        return build_sectioned_choose_schema(
            self._get_sections(),
            input_fields,
            field_schema,
            section_inclusion_map,
            current_data=subentry_data,
            extra_field_entries={
                SECTION_COMMON: build_common_fields(
                    include_connection=True,
                    participants=participants,
                    current_connection=current_connection,
                )
            },
        )

    def _build_defaults(
        self,
        default_name: str,
        input_fields: InputFieldGroups,
        subentry_data: dict[str, Any] | None = None,
        connection_default: str | None = None,
    ) -> dict[str, Any]:
        """Build default values for the form."""
        common_data = subentry_data.get(SECTION_COMMON, {}) if subentry_data else {}
        connection_default = (
            connection_default
            if connection_default is not None
            else get_connection_target_name(common_data.get(CONF_CONNECTION))
            if subentry_data
            else None
        )
        return build_sectioned_choose_defaults(
            self._get_sections(),
            input_fields,
            current_data=subentry_data,
            base_defaults={
                SECTION_COMMON: {
                    CONF_NAME: default_name if subentry_data is None else common_data.get(CONF_NAME),
                    CONF_CONNECTION: connection_default,
                },
                SECTION_CURTAILMENT: {},
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
        field_schema = get_input_field_schema_info(ElementType.SOLAR, input_fields)
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
        common_config = config_dict.get(SECTION_COMMON, {})
        if CONF_CONNECTION in common_config:
            common_config[CONF_CONNECTION] = normalize_connection_target(common_config[CONF_CONNECTION])

        return {
            CONF_ELEMENT_TYPE: ElementType.SOLAR,
            **config_dict,
        }

    def _finalize(self, config: dict[str, Any], user_input: dict[str, Any]) -> SubentryFlowResult:
        """Finalize the flow by creating or updating the entry."""
        name = str(user_input.get(SECTION_COMMON, {}).get(CONF_NAME))
        subentry = self._get_subentry()
        if subentry is not None:
            return self.async_update_and_abort(self._get_entry(), subentry, title=name, data=config)
        return self.async_create_entry(title=name, data=config)
