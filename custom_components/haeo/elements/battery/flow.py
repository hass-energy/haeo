"""Battery element configuration flows."""

from typing import Any

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import BooleanSelector, BooleanSelectorConfig
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.elements.field_schema import FieldSchemaInfo
from custom_components.haeo.elements import get_input_field_schema_info
from custom_components.haeo.elements.input_fields import InputFieldGroups
from custom_components.haeo.flows.collection import (
    build_collection_names_schema,
    parse_collection_names,
    validate_collection_names,
)
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_sectioned_inclusion_map
from custom_components.haeo.flows.field_schema import (
    SectionDefinition,
    build_sectioned_choose_defaults,
    build_sectioned_choose_schema,
    convert_sectioned_choose_data_to_config,
    preprocess_sectioned_choose_input,
    validate_sectioned_choose_fields,
    is_valid_choose_value,
)
from custom_components.haeo.schema import (
    ConstantValue,
    EntityValue,
    NoneValue,
    get_connection_target_name,
    normalize_connection_target,
)
from custom_components.haeo.sections import (
    CONF_CONNECTION,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    build_common_fields,
    common_section,
    efficiency_section,
    power_limits_section,
    pricing_section,
)

from .adapter import adapter
from .schema import (
    CONF_CAPACITY,
    CONF_CHARGE_PRICE,
    CONF_CHARGE_VIOLATION_PRICE,
    CONF_CONFIGURE_PARTITIONS,
    CONF_DISCHARGE_PRICE,
    CONF_DISCHARGE_VIOLATION_PRICE,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_PARTITION_NAMES,
    CONF_SALVAGE_VALUE,
    CONF_THRESHOLD_KWH,
    ELEMENT_TYPE,
    SECTION_LIMITS,
    SECTION_PARTITIONING,
    SECTION_PARTITIONS,
    SECTION_STORAGE,
)

SECTION_ZONE = "zone"

ZONE_SECTION_DEFINITION = (
    SectionDefinition(
        key=SECTION_ZONE,
        fields=(
            CONF_THRESHOLD_KWH,
            CONF_CHARGE_VIOLATION_PRICE,
            CONF_DISCHARGE_VIOLATION_PRICE,
            CONF_CHARGE_PRICE,
            CONF_DISCHARGE_PRICE,
        ),
        collapsed=False,
    ),
)

ZONE_FIELD_SCHEMA: dict[str, dict[str, FieldSchemaInfo]] = {
    SECTION_ZONE: {
        CONF_THRESHOLD_KWH: FieldSchemaInfo(value_type=EntityValue | ConstantValue, is_optional=False),
        CONF_CHARGE_VIOLATION_PRICE: FieldSchemaInfo(value_type=EntityValue | ConstantValue | NoneValue, is_optional=True),
        CONF_DISCHARGE_VIOLATION_PRICE: FieldSchemaInfo(
            value_type=EntityValue | ConstantValue | NoneValue, is_optional=True
        ),
        CONF_CHARGE_PRICE: FieldSchemaInfo(value_type=EntityValue | ConstantValue | NoneValue, is_optional=True),
        CONF_DISCHARGE_PRICE: FieldSchemaInfo(value_type=EntityValue | ConstantValue | NoneValue, is_optional=True),
    }
}


class BatterySubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle battery element configuration flows."""

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        self._step1_data: dict[str, Any] = {}
        self._partition_names: list[str] = []
        self._partition_index: int = 0
        self._partition_config: dict[str, dict[str, Any]] = {}

    def _get_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the main configuration step."""
        return (
            common_section((CONF_NAME, CONF_CONNECTION), collapsed=False),
            SectionDefinition(
                key=SECTION_STORAGE, fields=(CONF_CAPACITY, CONF_INITIAL_CHARGE_PERCENTAGE), collapsed=False
            ),
            SectionDefinition(
                key=SECTION_LIMITS,
                fields=(
                    CONF_MIN_CHARGE_PERCENTAGE,
                    CONF_MAX_CHARGE_PERCENTAGE,
                ),
                collapsed=False,
            ),
            power_limits_section((CONF_MAX_POWER_TARGET_SOURCE, CONF_MAX_POWER_SOURCE_TARGET), collapsed=False),
            pricing_section((CONF_PRICE_SOURCE_TARGET, CONF_PRICE_TARGET_SOURCE, CONF_SALVAGE_VALUE), collapsed=False),
            efficiency_section((CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE), collapsed=True),
            SectionDefinition(key=SECTION_PARTITIONING, fields=(CONF_CONFIGURE_PARTITIONS,), collapsed=True),
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
        default_name = await self._async_get_default_name(ELEMENT_TYPE)
        if not isinstance(current_connection, str):
            current_connection = participants[0] if participants else ""

        input_fields = adapter.inputs(subentry_data)

        sections = self._get_sections()
        user_input = preprocess_sectioned_choose_input(user_input, input_fields, sections)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            self._step1_data = user_input
            # Check if partitions are enabled
            if user_input.get(SECTION_PARTITIONING, {}).get(CONF_CONFIGURE_PARTITIONS):
                return await self.async_step_partition_names()
            # No partitions - finalize directly
            config = self._build_config(user_input)
            return self._finalize(config)

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

    async def async_step_partition_names(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Collect SOC zone names (one per line)."""
        subentry = self._get_subentry()
        subentry_data = dict(subentry.data) if subentry else None

        errors: dict[str, str] | None = None
        if user_input is not None:
            raw = str(user_input.get(CONF_PARTITION_NAMES, ""))
            names = parse_collection_names(raw)
            errors = validate_collection_names(names)
            if errors is None:
                self._partition_names = names
                self._partition_index = 0
                self._partition_config = {}
                return await self.async_step_partition()

        schema = build_collection_names_schema(CONF_PARTITION_NAMES)

        existing = ""
        if subentry_data:
            partitions = subentry_data.get(SECTION_PARTITIONS, {})
            if isinstance(partitions, dict) and partitions:
                existing = "\n".join(str(k) for k in partitions)

        defaults = user_input if user_input is not None else {CONF_PARTITION_NAMES: existing}
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="partition_names", data_schema=schema, errors=errors)

    async def async_step_partition(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Configure a single SOC zone, looping for all zone names."""
        if not self._partition_names:
            return await self.async_step_partition_names()

        zone_name = self._partition_names[self._partition_index]

        subentry = self._get_subentry()
        subentry_data = dict(subentry.data) if subentry else None
        existing_zone: dict[str, Any] | None = None
        if subentry_data:
            partitions = subentry_data.get(SECTION_PARTITIONS, {})
            if isinstance(partitions, dict):
                candidate = partitions.get(zone_name)
                if isinstance(candidate, dict):
                    existing_zone = candidate

        input_fields = adapter.zone_inputs()
        user_input = preprocess_sectioned_choose_input(user_input, input_fields, ZONE_SECTION_DEFINITION)
        errors = self._validate_zone_input(user_input)

        if user_input is not None and not errors:
            zone_sectioned = convert_sectioned_choose_data_to_config(
                user_input,
                input_fields,
                ZONE_SECTION_DEFINITION,
            )
            zone_config = zone_sectioned.get(SECTION_ZONE, {})
            if isinstance(zone_config, dict):
                self._partition_config[zone_name] = zone_config

            self._partition_index += 1
            if self._partition_index < len(self._partition_names):
                return await self.async_step_partition()

            # Finished all zones - finalize config
            config = self._build_config(self._step1_data, partitions=self._partition_config)
            return self._finalize(config)

        entity_metadata = extract_entity_metadata(self.hass)
        section_inclusion_map = build_sectioned_inclusion_map(input_fields, entity_metadata)
        schema = build_sectioned_choose_schema(
            ZONE_SECTION_DEFINITION,
            input_fields,
            ZONE_FIELD_SCHEMA,
            section_inclusion_map,
            current_data={SECTION_ZONE: existing_zone or {}},
        )
        defaults = user_input if user_input is not None else self._build_zone_defaults(input_fields, existing_zone)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="partition",
            data_schema=schema,
            errors=errors,
            description_placeholders={"partition_name": zone_name},
        )

    def _build_schema(
        self,
        participants: list[str],
        input_fields: InputFieldGroups,
        section_inclusion_map: dict[str, dict[str, list[str]]],
        current_connection: str | None = None,
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema with name, connection, and choose selectors for main inputs."""
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
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
                ),
                SECTION_PARTITIONING: {
                    CONF_CONFIGURE_PARTITIONS: (
                        vol.Optional(CONF_CONFIGURE_PARTITIONS),
                        BooleanSelector(BooleanSelectorConfig()),
                    )
                },
            },
        )

    def _build_defaults(
        self,
        default_name: str,
        input_fields: InputFieldGroups,
        subentry_data: dict[str, Any] | None = None,
        connection_default: str | None = None,
    ) -> dict[str, Any]:
        """Build default values for the main form."""
        common_data = subentry_data.get(SECTION_COMMON, {}) if subentry_data else {}
        connection_default = (
            connection_default
            if connection_default is not None
            else get_connection_target_name(common_data.get(CONF_CONNECTION))
            if subentry_data
            else None
        )
        # Check if partitions were previously configured
        has_partitions = bool(subentry_data.get(SECTION_PARTITIONS)) if subentry_data else False
        return build_sectioned_choose_defaults(
            self._get_sections(),
            input_fields,
            current_data=subentry_data,
            base_defaults={
                SECTION_COMMON: {
                    CONF_NAME: default_name if subentry_data is None else common_data.get(CONF_NAME),
                    CONF_CONNECTION: connection_default,
                },
                SECTION_PARTITIONING: {
                    CONF_CONFIGURE_PARTITIONS: has_partitions,
                },
            },
        )

    def _build_zone_defaults(
        self, input_fields: InputFieldGroups, current_zone: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Build default values for a single zone form."""
        return build_sectioned_choose_defaults(
            ZONE_SECTION_DEFINITION,
            input_fields,
            current_data={SECTION_ZONE: current_zone or {}},
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

    def _validate_zone_input(self, user_input: dict[str, Any] | None) -> dict[str, str] | None:
        """Validate a single zone's configuration."""
        if user_input is None:
            return None

        errors = validate_sectioned_choose_fields(
            user_input,
            adapter.zone_inputs(),
            ZONE_FIELD_SCHEMA,
            ZONE_SECTION_DEFINITION,
        )

        zone_input = user_input.get(SECTION_ZONE, {})
        if isinstance(zone_input, dict):
            has_charge_violation = is_valid_choose_value(zone_input.get(CONF_CHARGE_VIOLATION_PRICE))
            has_discharge_violation = is_valid_choose_value(zone_input.get(CONF_DISCHARGE_VIOLATION_PRICE))
            if not has_charge_violation and not has_discharge_violation:
                errors["base"] = "missing_zone_violation_price"

        return errors if errors else None

    def _build_config(
        self,
        main_input: dict[str, Any],
        *,
        partitions: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Build final config dict from user input."""
        input_fields = adapter.inputs(main_input)
        config_dict = convert_sectioned_choose_data_to_config(main_input, input_fields, self._get_sections())

        common_config = config_dict.get(SECTION_COMMON, {})
        if CONF_CONNECTION in common_config:
            common_config[CONF_CONNECTION] = normalize_connection_target(common_config[CONF_CONNECTION])

        if partitions:
            config_dict[SECTION_PARTITIONS] = partitions

        return {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE,
            **config_dict,
        }

    def _finalize(self, config: dict[str, Any]) -> SubentryFlowResult:
        """Finalize the flow by creating or updating the entry."""
        name = str(self._step1_data.get(SECTION_COMMON, {}).get(CONF_NAME))
        subentry = self._get_subentry()
        if subentry is not None:
            return self.async_update_and_abort(self._get_entry(), subentry, title=name, data=config)
        return self.async_create_entry(title=name, data=config)
