"""Connection element configuration flows."""

from typing import Any

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import get_connection_target_name, normalize_connection_target
from custom_components.haeo.core.schema.elements.connection import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    SECTION_ENDPOINTS,
)
from custom_components.haeo.elements import get_input_field_schema_info, get_input_fields
from custom_components.haeo.elements.input_fields import InputFieldGroups
from custom_components.haeo.flows.element_flow import (
    ElementFlowMixin,
    build_participant_selector,
    build_sectioned_inclusion_map,
)
from custom_components.haeo.flows.entity_metadata import extract_entity_metadata
from custom_components.haeo.flows.field_schema import (
    SectionDefinition,
    build_sectioned_choose_defaults,
    build_sectioned_choose_schema,
    convert_sectioned_choose_data_to_config,
    preprocess_sectioned_choose_input,
    validate_sectioned_choose_fields,
)
from custom_components.haeo.sections import (
    build_common_fields,
    efficiency_section,
    power_limits_section,
    pricing_section,
)


def _build_endpoints_fields(
    participants: list[str],
    current_source: str | None = None,
    current_target: str | None = None,
) -> dict[str, tuple[vol.Marker, Any]]:
    """Build endpoint field entries for config flows."""
    return {
        CONF_SOURCE: (
            vol.Required(CONF_SOURCE),
            build_participant_selector(participants, current_source),
        ),
        CONF_TARGET: (
            vol.Required(CONF_TARGET),
            build_participant_selector(participants, current_target),
        ),
    }


class ConnectionSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle connection element configuration flows."""

    def _get_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the configuration step."""
        return (
            SectionDefinition(key=SECTION_ENDPOINTS, fields=(CONF_SOURCE, CONF_TARGET), collapsed=False),
            power_limits_section((CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE), collapsed=False),
            pricing_section((CONF_PRICE_SOURCE_TARGET, CONF_PRICE_TARGET_SOURCE), collapsed=False),
            efficiency_section((CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE), collapsed=True),
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle user step: name, source, target, and input configuration."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step: name, source, target, and input configuration."""
        return await self._async_step_user(user_input)

    async def _async_step_user(self, user_input: dict[str, Any] | None) -> SubentryFlowResult:
        """Shared logic for user and reconfigure steps."""
        subentry = self._get_subentry()
        subentry_data = dict(subentry.data) if subentry else None
        participants = self._get_participant_names()
        current_source = (
            get_connection_target_name(subentry_data.get(SECTION_ENDPOINTS, {}).get(CONF_SOURCE))
            if subentry_data
            else None
        )
        current_target = (
            get_connection_target_name(subentry_data.get(SECTION_ENDPOINTS, {}).get(CONF_TARGET))
            if subentry_data
            else None
        )
        default_name = await self._async_get_default_name(ELEMENT_TYPE)
        if not isinstance(current_source, str):
            current_source = participants[0] if participants else ""
        if not isinstance(current_target, str):
            current_target = participants[min(1, len(participants) - 1)] if participants else ""
        input_fields = get_input_fields(ELEMENT_TYPE)

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
            current_source,
            current_target,
            subentry_data,
        )
        defaults = (
            user_input
            if user_input is not None
            else self._build_defaults(
                default_name,
                input_fields,
                subentry_data,
                current_source,
                current_target,
            )
        )
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    def _build_schema(
        self,
        participants: list[str],
        input_fields: InputFieldGroups,
        section_inclusion_map: dict[str, dict[str, list[str]]],
        current_source: str | None = None,
        current_target: str | None = None,
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema with name, source, target, and choose selectors for inputs."""
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        return build_sectioned_choose_schema(
            self._get_sections(),
            input_fields,
            field_schema,
            section_inclusion_map,
            current_data=subentry_data,
            top_level_entries=build_common_fields(include_connection=False),
            extra_field_entries={
                SECTION_ENDPOINTS: _build_endpoints_fields(participants, current_source, current_target),
            },
        )

    def _build_defaults(
        self,
        default_name: str,
        input_fields: InputFieldGroups,
        subentry_data: dict[str, Any] | None = None,
        source_default: str | None = None,
        target_default: str | None = None,
    ) -> dict[str, Any]:
        """Build default values for the form."""
        endpoints_data = subentry_data.get(SECTION_ENDPOINTS, {}) if subentry_data else {}
        source_default = (
            source_default
            if source_default is not None
            else get_connection_target_name(endpoints_data.get(CONF_SOURCE))
            if subentry_data
            else None
        )
        target_default = (
            target_default
            if target_default is not None
            else get_connection_target_name(endpoints_data.get(CONF_TARGET))
            if subentry_data
            else None
        )
        return {
            CONF_NAME: default_name if subentry_data is None else subentry_data.get(CONF_NAME),
            **build_sectioned_choose_defaults(
                self._get_sections(),
                input_fields,
                current_data=subentry_data,
                base_defaults={
                    SECTION_ENDPOINTS: {
                        CONF_SOURCE: source_default,
                        CONF_TARGET: target_default,
                    },
                },
            ),
        }

    def _validate_user_input(
        self,
        user_input: dict[str, Any] | None,
        input_fields: InputFieldGroups,
    ) -> dict[str, str] | None:
        """Validate user input and return errors dict if any."""
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        endpoints_input = user_input.get(SECTION_ENDPOINTS, {})
        self._validate_name(user_input.get(CONF_NAME), errors)
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        errors.update(
            validate_sectioned_choose_fields(
                user_input,
                input_fields,
                field_schema,
                self._get_sections(),
            )
        )
        # Validate source != target
        source = endpoints_input.get(CONF_SOURCE)
        target = endpoints_input.get(CONF_TARGET)
        source_name = get_connection_target_name(source)
        target_name = get_connection_target_name(target)
        if source_name and target_name and source_name == target_name:
            errors[CONF_TARGET] = "cannot_connect_to_self"
        return errors if errors else None

    def _build_config(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Build final config dict from user input."""
        input_fields = get_input_fields(ELEMENT_TYPE)
        config_dict = convert_sectioned_choose_data_to_config(
            user_input,
            input_fields,
            self._get_sections(),
        )
        endpoints_config = config_dict.get(SECTION_ENDPOINTS, {})
        if CONF_SOURCE in endpoints_config:
            endpoints_config[CONF_SOURCE] = normalize_connection_target(endpoints_config[CONF_SOURCE])
        if CONF_TARGET in endpoints_config:
            endpoints_config[CONF_TARGET] = normalize_connection_target(endpoints_config[CONF_TARGET])

        return {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE,
            CONF_NAME: user_input[CONF_NAME],
            **config_dict,
        }

    def _finalize(self, config: dict[str, Any], user_input: dict[str, Any]) -> SubentryFlowResult:
        """Finalize the flow by creating or updating the entry."""
        name = str(user_input[CONF_NAME])
        subentry = self._get_subentry()
        if subentry is not None:
            return self.async_update_and_abort(self._get_entry(), subentry, title=name, data=config)
        return self.async_create_entry(title=name, data=config)
