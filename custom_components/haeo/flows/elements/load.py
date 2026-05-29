"""Load element configuration flows."""

from typing import Any

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
import voluptuous as vol

from custom_components.haeo.const import URL_HAFO
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import get_connection_target_name, normalize_connection_target
from custom_components.haeo.core.schema.elements.load import CONF_CONSUMPTION_COST, ELEMENT_TYPE, SURFACED_PRICE_HINTS
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    SECTION_CURTAILMENT,
)
from custom_components.haeo.elements import get_input_field_schema_info, get_input_fields, get_surfaced_input_fields
from custom_components.haeo.elements.input_fields import InputFieldGroups
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_sectioned_inclusion_map
from custom_components.haeo.flows.entity_metadata import extract_entity_metadata
from custom_components.haeo.flows.field_schema import (
    SectionDefinition,
    build_sectioned_choose_defaults,
    build_sectioned_choose_schema,
    convert_sectioned_choose_data_to_config,
    preprocess_sectioned_choose_input,
    validate_sectioned_choose_fields,
)
from custom_components.haeo.flows.surfaced_policy import (
    build_surfaced_defaults,
    build_surfaced_schema_entries,
    save_surfaced_rules_from_input,
)
from custom_components.haeo.sections import build_common_fields, forecast_section

# Surfaced policy field names (not stored in load config)
SURFACED_POLICY_FIELDS: frozenset[str] = frozenset({CONF_CONSUMPTION_COST})


class LoadSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle load element configuration flows."""

    def _get_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the configuration step."""
        return (
            forecast_section((CONF_FORECAST,), collapsed=False),
            SectionDefinition(
                key=SECTION_CURTAILMENT, fields=(CONF_CURTAILMENT, CONF_CONSUMPTION_COST), collapsed=True
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
        current_connection = get_connection_target_name(subentry_data.get(CONF_CONNECTION)) if subentry_data else None
        default_name = await self._async_get_default_name(ELEMENT_TYPE)
        if not isinstance(current_connection, str):
            current_connection = participants[0] if participants else ""
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
            description_placeholders={"hafo_url": URL_HAFO},
        )

    def _build_schema(
        self,
        participants: list[str],
        input_fields: InputFieldGroups,
        section_inclusion_map: dict[str, dict[str, list[str]]],
        current_connection: str | None = None,
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema with name, connection, and choose selectors for inputs."""
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        surfaced_fields = get_surfaced_input_fields(ELEMENT_TYPE)
        surfaced_entries = build_surfaced_schema_entries(surfaced_fields)
        return build_sectioned_choose_schema(
            self._get_sections(),
            input_fields,
            field_schema,
            section_inclusion_map,
            current_data=subentry_data,
            top_level_entries=build_common_fields(
                include_connection=True,
                participants=participants,
                current_connection=current_connection,
            ),
            extra_field_entries={
                SECTION_CURTAILMENT: surfaced_entries,
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
        connection_default = (
            connection_default
            if connection_default is not None
            else get_connection_target_name(subentry_data.get(CONF_CONNECTION))
            if subentry_data
            else None
        )
        hub_entry = self._get_entry()
        element_name = subentry_data.get(CONF_NAME) if subentry_data else None
        surfaced_fields = get_surfaced_input_fields(ELEMENT_TYPE)
        surfaced_defaults = build_surfaced_defaults(hub_entry, element_name, SURFACED_PRICE_HINTS, surfaced_fields)
        return {
            CONF_NAME: default_name if subentry_data is None else subentry_data.get(CONF_NAME),
            CONF_CONNECTION: connection_default,
            **build_sectioned_choose_defaults(
                self._get_sections(),
                input_fields,
                current_data=subentry_data,
                base_defaults={
                    SECTION_CURTAILMENT: surfaced_defaults,
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
        self._validate_name(user_input.get(CONF_NAME), errors)
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        errors.update(
            validate_sectioned_choose_fields(
                user_input,
                input_fields,
                field_schema,
                self._get_sections(),
                exclude_fields=tuple(SURFACED_POLICY_FIELDS),
            )
        )
        return errors if errors else None

    def _build_config(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Build final config dict from user input."""
        input_fields = get_input_fields(ELEMENT_TYPE)
        config_dict = convert_sectioned_choose_data_to_config(
            user_input,
            input_fields,
            self._get_sections(),
            exclude_fields=tuple(SURFACED_POLICY_FIELDS),
        )
        return {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE,
            CONF_NAME: user_input[CONF_NAME],
            CONF_CONNECTION: normalize_connection_target(user_input[CONF_CONNECTION]),
            **config_dict,
        }

    def _finalize(self, config: dict[str, Any], user_input: dict[str, Any]) -> SubentryFlowResult:
        """Finalize the flow by creating or updating the entry and saving surfaced rules."""
        name = str(user_input[CONF_NAME])

        # Save surfaced policy rules from the curtailment section input
        curtailment_input = user_input.get(SECTION_CURTAILMENT, {})
        hub_entry = self._get_entry()
        translations = {"consumption_cost": f"{name} consumption cost"}
        subentry = self._get_subentry()
        is_new = subentry is None
        save_surfaced_rules_from_input(
            self.hass,
            hub_entry,
            name,
            curtailment_input,
            SURFACED_PRICE_HINTS,
            translations,
            apply_defaults=is_new,
        )

        if subentry is not None:
            return self.async_update_and_abort(self._get_entry(), subentry, title=name, data=config)
        return self.async_create_entry(title=name, data=config)
