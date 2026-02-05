"""Battery section element configuration flows."""

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult, UnknownSubEntry
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.elements import is_element_config_schema
from custom_components.haeo.elements.input_fields import InputFieldGroups
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_sectioned_inclusion_map
from custom_components.haeo.flows.field_schema import (
    SectionDefinition,
    build_choose_field_entries,
    build_section_schema,
    convert_sectioned_choose_data_to_config,
    get_choose_default,
    preprocess_sectioned_choose_input,
    validate_sectioned_choose_fields,
)
from custom_components.haeo.sections import SECTION_COMMON, build_common_fields, common_section

from .adapter import adapter
from .schema import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    ELEMENT_TYPE,
    OPTIONAL_INPUT_FIELDS,
    SECTION_STORAGE,
    BatterySectionConfigSchema,
)


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
            element_config: BatterySectionConfigSchema = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                SECTION_COMMON: {CONF_NAME: default_name},
                SECTION_STORAGE: {
                    CONF_CAPACITY: 0.0,
                    CONF_INITIAL_CHARGE: 0.0,
                },
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
            input_fields,
            section_inclusion_map,
            dict(subentry_data) if subentry_data is not None else None,
        )
        defaults = (
            user_input
            if user_input is not None
            else self._build_defaults(
                default_name,
                dict(subentry_data) if subentry_data is not None else None,
            )
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
        sections = self._get_sections()
        field_entries: dict[str, dict[str, tuple[vol.Marker, Any]]] = {
            SECTION_COMMON: build_common_fields(include_connection=False),
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

    def _build_defaults(
        self,
        default_name: str,
        subentry_data: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build default values for the form."""
        common_data = subentry_data.get(SECTION_COMMON, {}) if subentry_data else {}
        defaults: dict[str, Any] = {
            SECTION_COMMON: {
                CONF_NAME: default_name if subentry_data is None else common_data.get(CONF_NAME),
            },
            SECTION_STORAGE: {},
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
        common_input = user_input.get(SECTION_COMMON, {})
        self._validate_name(common_input.get(CONF_NAME), errors)
        errors.update(
            validate_sectioned_choose_fields(
                user_input,
                input_fields,
                OPTIONAL_INPUT_FIELDS,
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

    def _get_subentry(self) -> ConfigSubentry | None:
        """Get the subentry being reconfigured, or None for new entries."""
        try:
            return self._get_reconfigure_subentry()
        except (ValueError, UnknownSubEntry):
            return None
