"""Grid element configuration flows."""

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult, UnknownSubEntry
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.elements import is_element_config_schema
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_inclusion_map, build_participant_selector
from custom_components.haeo.flows.field_schema import (
    SectionDefinition,
    build_choose_field_entries,
    build_section_schema,
    get_choose_default,
    preprocess_sectioned_choose_input,
    convert_sectioned_choose_data_to_config,
    validate_sectioned_choose_fields,
)

from .adapter import adapter
from .schema import (
    CONF_CONNECTION,
    CONF_EXPORT_LIMIT,
    CONF_EXPORT_PRICE,
    CONF_IMPORT_LIMIT,
    CONF_IMPORT_PRICE,
    CONF_SECTION_BASIC,
    CONF_SECTION_LIMITS,
    CONF_SECTION_PRICING,
    ELEMENT_TYPE,
    OPTIONAL_INPUT_FIELDS,
    GridConfigSchema,
)


class GridSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle grid element configuration flows."""

    def _get_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the configuration step."""
        return (
            SectionDefinition(
                key="basic",
                fields=(CONF_NAME, CONF_CONNECTION),
                collapsed=False,
            ),
            SectionDefinition(
                key="pricing",
                fields=(CONF_IMPORT_PRICE, CONF_EXPORT_PRICE),
                collapsed=False,
            ),
            SectionDefinition(
                key="limits",
                fields=(CONF_IMPORT_LIMIT, CONF_EXPORT_LIMIT),
                collapsed=True,
            ),
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
            subentry_data.get(CONF_SECTION_BASIC, {}).get(CONF_CONNECTION) if subentry_data else None
        )

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
            if not isinstance(current_connection, str):
                current_connection = participants[0] if participants else ""
            element_config: GridConfigSchema = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_SECTION_BASIC: {
                    CONF_NAME: default_name,
                    CONF_CONNECTION: current_connection,
                },
                CONF_SECTION_PRICING: {
                    CONF_IMPORT_PRICE: 0.0,
                    CONF_EXPORT_PRICE: 0.0,
                },
                CONF_SECTION_LIMITS: {},
            }

        input_fields = adapter.inputs(element_config)

        # Preprocess to normalize ChooseSelector data before validation
        sections = self._get_sections()
        user_input = preprocess_sectioned_choose_input(user_input, input_fields, sections)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            config = self._build_config(
                user_input,
                dict(subentry_data) if subentry_data is not None else None,
            )
            return self._finalize(config, user_input)

        entity_metadata = extract_entity_metadata(self.hass)
        inclusion_map = build_inclusion_map(input_fields, entity_metadata)
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
        )
        default_name = translations[f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title"]

        schema = self._build_schema(
            participants,
            input_fields,
            inclusion_map,
            current_connection,
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
        participants: list[str],
        input_fields: Mapping[str, InputFieldInfo[Any]],
        inclusion_map: dict[str, list[str]],
        current_connection: str | None = None,
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema with name, connection, and choose selectors for inputs."""
        sections = self._get_sections()
        field_entries: dict[str, tuple[vol.Marker, Any]] = {
            CONF_NAME: (
                vol.Required(CONF_NAME),
                vol.All(
                    vol.Coerce(str),
                    vol.Strip,
                    vol.Length(min=1, msg="Name cannot be empty"),
                    TextSelector(TextSelectorConfig()),
                ),
            ),
            CONF_CONNECTION: (
                vol.Required(CONF_CONNECTION),
                build_participant_selector(participants, current_connection),
            ),
        }

        field_entries.update(
            build_choose_field_entries(
                input_fields,
                optional_fields=OPTIONAL_INPUT_FIELDS,
                inclusion_map=inclusion_map,
                current_data=subentry_data,
            )
        )

        return vol.Schema(build_section_schema(sections, field_entries))

    def _build_defaults(
        self,
        default_name: str,
        subentry_data: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build default values for the form."""
        basic_data = subentry_data.get(CONF_SECTION_BASIC, {}) if subentry_data else {}
        defaults: dict[str, Any] = {
            CONF_SECTION_BASIC: {
                CONF_NAME: default_name if subentry_data is None else basic_data.get(CONF_NAME),
                CONF_CONNECTION: basic_data.get(CONF_CONNECTION) if subentry_data else None,
            },
            CONF_SECTION_PRICING: {},
            CONF_SECTION_LIMITS: {},
        }

        input_fields = adapter.inputs(subentry_data)
        section_map = {
            field_name: section.key
            for section in self._get_sections()
            for field_name in section.fields
        }
        for field_info in input_fields.values():
            choose_default = get_choose_default(field_info, subentry_data)
            if choose_default is not None:
                section_key = section_map.get(field_info.field_name)
                if section_key:
                    defaults.setdefault(section_key, {})[field_info.field_name] = choose_default

        return defaults

    def _validate_user_input(
        self,
        user_input: dict[str, Any] | None,
        input_fields: Mapping[str, InputFieldInfo[Any]],
    ) -> dict[str, str] | None:
        """Validate user input and return errors dict if any."""
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        basic_input = user_input.get(CONF_SECTION_BASIC, {})
        self._validate_name(basic_input.get(CONF_NAME), errors)
        errors.update(
            validate_sectioned_choose_fields(
                user_input,
                input_fields,
                OPTIONAL_INPUT_FIELDS,
                self._get_sections(),
            )
        )
        return errors if errors else None

    def _build_config(
        self,
        user_input: dict[str, Any],
        current_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build final config dict from user input."""
        input_fields = adapter.inputs(current_data or user_input)
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
        name = str(user_input.get(CONF_SECTION_BASIC, {}).get(CONF_NAME))
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
