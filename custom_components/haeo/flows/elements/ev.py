"""EV element configuration flows."""

from collections.abc import Mapping
from typing import Any  # noqa: TID251  # HA flow signatures are Any-typed upstream

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import get_connection_target_name, normalize_connection_target
from custom_components.haeo.core.schema.elements.ev import (
    CONF_CAPACITY,
    CONF_CONNECTED,
    CONF_CURRENT_SOC,
    CONF_ENERGY_PER_DISTANCE,
    CONF_MAX_CHARGE_RATE,
    CONF_MAX_DISCHARGE_RATE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_ODOMETER,
    CONF_PUBLIC_CHARGING_PRICE,
    CONF_TRIP_CALENDAR,
    ELEMENT_TYPE,
    SECTION_CHARGING,
    SECTION_PUBLIC_CHARGING,
    SECTION_TRIP,
    SECTION_VEHICLE,
)
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
)
from custom_components.haeo.elements import get_input_field_schema_info
from custom_components.haeo.elements.input_fields import InputFieldGroups
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_sectioned_inclusion_map
from custom_components.haeo.flows.entity_metadata import extract_entity_metadata
from custom_components.haeo.flows.field_schema import (
    SectionDefinition,
    as_str,
    build_sectioned_choose_defaults,
    build_sectioned_choose_schema,
    convert_sectioned_choose_data_to_config,
    preprocess_sectioned_choose_input,
    sectioned_view,
    validate_sectioned_choose_fields,
)
from custom_components.haeo.sections import build_common_fields, efficiency_section


class EvSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle EV element configuration flows."""

    def _get_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the configuration step."""
        return (
            SectionDefinition(
                key=SECTION_VEHICLE,
                fields=(CONF_CAPACITY, CONF_ENERGY_PER_DISTANCE, CONF_CURRENT_SOC, CONF_MIN_CHARGE_PERCENTAGE),
                collapsed=False,
            ),
            SectionDefinition(
                key=SECTION_CHARGING,
                fields=(CONF_MAX_CHARGE_RATE, CONF_MAX_DISCHARGE_RATE, CONF_CONNECTED),
                collapsed=False,
            ),
            SectionDefinition(
                key=SECTION_TRIP,
                fields=(
                    CONF_TRIP_CALENDAR,
                    CONF_ODOMETER,
                ),
                collapsed=True,
            ),
            SectionDefinition(
                key=SECTION_PUBLIC_CHARGING,
                fields=(CONF_PUBLIC_CHARGING_PRICE,),
                collapsed=True,
            ),
            efficiency_section(
                (CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE),
                collapsed=True,
            ),
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle user step: name, connection, trip entities, and input configuration."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step."""
        return await self._async_step_user(user_input)

    async def _async_step_user(self, user_input: dict[str, object] | None) -> SubentryFlowResult:
        """Shared logic for user and reconfigure steps."""
        subentry = self._get_subentry()
        subentry_data: dict[str, object] | None = dict(subentry.data) if subentry else None
        participants = self._get_participant_names()
        current_connection = (
            get_connection_target_name(subentry_data.get(CONF_CONNECTION))  # type: ignore[arg-type]  # stored subentry data always matches EvConfigSchema
            if subentry_data
            else None
        )
        default_name = await self._async_get_default_name(ELEMENT_TYPE)
        if not isinstance(current_connection, str):
            current_connection = participants[0] if participants else ""
        input_fields = self._get_input_fields(ELEMENT_TYPE)

        sections = self._get_sections()
        user_input = preprocess_sectioned_choose_input(user_input, input_fields, sections)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            config = self._build_config(user_input)
            return self._finalize(config, user_input)

        entity_metadata = extract_entity_metadata(self.hass, self._get_entry())
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
        subentry_data: Mapping[str, object] | None = None,
    ) -> vol.Schema:
        """Build the schema with name, connection, trip entities, and choose selectors."""
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        top_level = {
            **build_common_fields(
                include_connection=True,
                participants=participants,
                current_connection=current_connection,
            ),
        }
        return build_sectioned_choose_schema(
            self._get_sections(),
            input_fields,
            field_schema,
            section_inclusion_map,
            current_data=sectioned_view(subentry_data),
            top_level_entries=top_level,
        )

    def _build_defaults(
        self,
        default_name: str,
        input_fields: InputFieldGroups,
        subentry_data: Mapping[str, object] | None = None,
        connection_default: str | None = None,
    ) -> dict[str, object]:
        """Build default values for the form."""
        connection_default = (
            connection_default
            if connection_default is not None
            else get_connection_target_name(subentry_data.get(CONF_CONNECTION))  # type: ignore[arg-type]  # stored subentry data always matches EvConfigSchema
            if subentry_data
            else None
        )
        return {
            CONF_NAME: default_name if subentry_data is None else subentry_data.get(CONF_NAME),
            CONF_CONNECTION: connection_default,
            **build_sectioned_choose_defaults(
                self._get_sections(),
                input_fields,
                current_data=subentry_data,
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
        self._validate_endpoint(as_str(user_input.get(CONF_CONNECTION)), CONF_CONNECTION, errors)
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

    def _build_config(self, user_input: Mapping[str, object]) -> dict[str, object]:
        """Build final config dict from user input."""
        input_fields = self._get_input_fields(ELEMENT_TYPE)
        config_dict = convert_sectioned_choose_data_to_config(
            user_input,
            input_fields,
            self._get_sections(),
        )
        return {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE,
            CONF_NAME: user_input[CONF_NAME],
            CONF_CONNECTION: normalize_connection_target(user_input[CONF_CONNECTION]),  # type: ignore[arg-type]  # user input validated by choose selector against the connection schema
            **config_dict,
        }

    def _finalize(self, config: dict[str, object], user_input: Mapping[str, object]) -> SubentryFlowResult:
        """Finalize the flow by creating or updating the entry."""
        name = str(user_input[CONF_NAME])
        subentry = self._get_subentry()
        if subentry is not None:
            return self.async_update_and_abort(self._get_entry(), subentry, title=name, data=config)
        return self.async_create_entry(title=name, data=config)
