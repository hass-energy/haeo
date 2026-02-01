"""Connection element configuration flows."""

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult, UnknownSubEntry
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.elements import is_element_config_schema
from custom_components.haeo.elements.input_fields import InputFieldGroups
from custom_components.haeo.flows.element_flow import (
    ElementFlowMixin,
    build_participant_selector,
    build_sectioned_inclusion_map,
)
from custom_components.haeo.flows.field_schema import (
    SectionDefinition,
    build_choose_field_entries,
    build_section_schema,
    convert_sectioned_choose_data_to_config,
    get_choose_default,
    preprocess_sectioned_choose_input,
    validate_sectioned_choose_fields,
)
from custom_components.haeo.sections import (
    SECTION_ADVANCED,
    SECTION_BASIC,
    SECTION_LIMITS,
    SECTION_PRICING,
    advanced_section,
    basic_section,
    build_name_field,
    limits_section,
    pricing_section,
)

from .adapter import adapter
from .schema import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    OPTIONAL_INPUT_FIELDS,
    SECTION_ENDPOINTS,
    ConnectionConfigSchema,
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
            basic_section((CONF_NAME,), collapsed=False),
            SectionDefinition(key=SECTION_ENDPOINTS, fields=(CONF_SOURCE, CONF_TARGET), collapsed=False),
            limits_section((CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE), collapsed=False),
            pricing_section((CONF_PRICE_SOURCE_TARGET, CONF_PRICE_TARGET_SOURCE), collapsed=False),
            advanced_section((CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE), collapsed=True),
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
        current_source = subentry_data.get(SECTION_ENDPOINTS, {}).get(CONF_SOURCE) if subentry_data else None
        current_target = subentry_data.get(SECTION_ENDPOINTS, {}).get(CONF_TARGET) if subentry_data else None

        if (
            subentry_data is not None
            and is_element_config_schema(subentry_data)
            and subentry_data["element_type"] == ELEMENT_TYPE
        ):
            element_config = subentry_data
        else:
            translations = await async_get_translations(
                self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
            )
            default_name = translations[f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title"]
            if not isinstance(current_source, str):
                current_source = participants[0] if participants else ""
            if not isinstance(current_target, str):
                current_target = participants[min(1, len(participants) - 1)] if participants else ""
            element_config: ConnectionConfigSchema = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                SECTION_BASIC: {
                    CONF_NAME: default_name,
                },
                SECTION_ENDPOINTS: {
                    CONF_SOURCE: current_source,
                    CONF_TARGET: current_target,
                },
                SECTION_LIMITS: {},
                SECTION_PRICING: {},
                SECTION_ADVANCED: {},
            }

        input_fields = adapter.inputs(element_config)

        sections = self._get_sections()
        user_input = preprocess_sectioned_choose_input(user_input, input_fields, sections)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            config = self._build_config(user_input)
            return self._finalize(config, user_input)

        entity_metadata = extract_entity_metadata(self.hass)
        section_inclusion_map = build_sectioned_inclusion_map(input_fields, entity_metadata)
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
        )
        default_name = translations[f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title"]

        schema = self._build_schema(
            participants,
            input_fields,
            section_inclusion_map,
            current_source,
            current_target,
            dict(subentry_data) if subentry_data is not None else None,
        )
        flat_defaults = (
            user_input
            if user_input is not None
            else self._build_defaults(
                default_name,
                dict(subentry_data) if subentry_data is not None else None,
            )
        )
        schema = self.add_suggested_values_to_schema(schema, flat_defaults)

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
        sections = self._get_sections()
        field_entries: dict[str, dict[str, tuple[vol.Marker, Any]]] = {
            SECTION_BASIC: {
                CONF_NAME: build_name_field(),
            },
            SECTION_ENDPOINTS: _build_endpoints_fields(participants, current_source, current_target),
        }

        for section_def in sections:
            section_fields = input_fields.get(section_def.key, {})
            if not section_fields:
                continue
            field_entries.setdefault(section_def.key, {}).update(
                build_choose_field_entries(
                    section_fields,
                    optional_fields=OPTIONAL_INPUT_FIELDS,
                    inclusion_map=section_inclusion_map.get(section_def.key, {}),
                    current_data=subentry_data.get(section_def.key) if subentry_data else None,
                )
            )

        return vol.Schema(build_section_schema(sections, field_entries))

    def _build_defaults(self, default_name: str, subentry_data: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Build default values for the form."""
        basic_data = subentry_data.get(SECTION_BASIC, {}) if subentry_data else {}
        endpoints_data = subentry_data.get(SECTION_ENDPOINTS, {}) if subentry_data else {}
        defaults: dict[str, Any] = {
            SECTION_BASIC: {
                CONF_NAME: default_name if subentry_data is None else basic_data.get(CONF_NAME),
            },
            SECTION_ENDPOINTS: {
                CONF_SOURCE: endpoints_data.get(CONF_SOURCE) if subentry_data else None,
                CONF_TARGET: endpoints_data.get(CONF_TARGET) if subentry_data else None,
            },
            SECTION_LIMITS: {},
            SECTION_PRICING: {},
            SECTION_ADVANCED: {},
        }

        input_fields = adapter.inputs(subentry_data)
        for section_key, section_fields in input_fields.items():
            for field_info in section_fields.values():
                choose_default = get_choose_default(
                    field_info,
                    subentry_data.get(section_key) if subentry_data else None,
                )
                if choose_default is not None:
                    defaults.setdefault(section_key, {})[field_info.field_name] = choose_default

        return defaults

    def _validate_user_input(
        self,
        user_input: dict[str, Any] | None,
        input_fields: InputFieldGroups,
    ) -> dict[str, str] | None:
        """Validate user input and return errors dict if any."""
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        basic_input = user_input.get(SECTION_BASIC, {})
        endpoints_input = user_input.get(SECTION_ENDPOINTS, {})
        self._validate_name(basic_input.get(CONF_NAME), errors)
        errors.update(
            validate_sectioned_choose_fields(
                user_input,
                input_fields,
                OPTIONAL_INPUT_FIELDS,
                self._get_sections(),
            )
        )
        # Validate source != target
        source = endpoints_input.get(CONF_SOURCE)
        target = endpoints_input.get(CONF_TARGET)
        if source and target and source == target:
            errors[CONF_TARGET] = "cannot_connect_to_self"
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
        name = str(user_input.get(SECTION_BASIC, {}).get(CONF_NAME))
        subentry = self._get_subentry()
        if subentry is not None:
            return self.async_update_and_abort(self._get_entry(), subentry, title=name, data=config)
        return self.async_create_entry(title=name, data=config)

    def _get_subentry(self) -> ConfigSubentry | None:
        """Get the subentry being reconfigured, or None for new entries."""
        try:
            return self._get_reconfigure_subentry()
        except (ValueError, UnknownSubEntry):
            return None
