"""Battery element configuration flows."""

from collections.abc import Mapping
from typing import Any  # noqa: TID251  # HA flow signatures are Any-typed upstream

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import BooleanSelector, BooleanSelectorConfig
import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import get_connection_target_name, normalize_connection_target
from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_CHARGE_COST,
    CONF_CONFIGURE_PARTITIONS,
    CONF_DISCHARGE_COST,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_PARTITION_COST,
    CONF_PARTITION_PERCENTAGE,
    CONF_SALVAGE_VALUE,
    ELEMENT_TYPE,
    PARTITION_FIELD_NAMES,
    SECTION_LIMITS,
    SECTION_OVERCHARGE,
    SECTION_PARTITIONING,
    SECTION_PRICING,
    SECTION_STORAGE,
    SECTION_UNDERCHARGE,
    SURFACED_PRICE_HINTS,
)
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
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
from custom_components.haeo.sections import (
    build_common_fields,
    efficiency_section,
    power_limits_section,
    pricing_section,
)

PARTITION_SECTION_DEFINITIONS = (
    SectionDefinition(
        key=SECTION_UNDERCHARGE,
        fields=(CONF_PARTITION_PERCENTAGE, CONF_PARTITION_COST),
        collapsed=False,
    ),
    SectionDefinition(
        key=SECTION_OVERCHARGE,
        fields=(CONF_PARTITION_PERCENTAGE, CONF_PARTITION_COST),
        collapsed=False,
    ),
)

# Surfaced policy field names (not stored in battery config)
SURFACED_POLICY_FIELDS: frozenset[str] = frozenset({CONF_CHARGE_COST, CONF_DISCHARGE_COST})


def _as_mapping(value: object) -> Mapping[str, object]:
    """Narrow a stored dict value to a mapping, defaulting to empty."""
    return value if isinstance(value, Mapping) else {}


def _as_str(value: object) -> str | None:
    """Narrow a stored dict value to a string, or None if absent/invalid."""
    return value if isinstance(value, str) else None


def _sectioned_view(data: Mapping[str, object] | None) -> Mapping[str, Mapping[str, object]] | None:
    """Narrow stored subentry data to only its nested section mappings."""
    if data is None:
        return None
    return {key: value for key, value in data.items() if isinstance(value, Mapping)}


class BatterySubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle battery element configuration flows."""

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        self._step1_data: dict[str, object] = {}

    def _get_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the main configuration step."""
        return (
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
            pricing_section((CONF_SALVAGE_VALUE, CONF_CHARGE_COST, CONF_DISCHARGE_COST), collapsed=False),
            efficiency_section((CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE), collapsed=True),
            SectionDefinition(key=SECTION_PARTITIONING, fields=(CONF_CONFIGURE_PARTITIONS,), collapsed=True),
        )

    def _get_partition_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the partition configuration step."""
        return PARTITION_SECTION_DEFINITIONS

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle user step: name, connection, and input configuration."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step: name, connection, and input configuration."""
        return await self._async_step_user(user_input)

    async def _async_step_user(self, user_input: dict[str, object] | None) -> SubentryFlowResult:
        """Shared logic for user and reconfigure steps."""
        subentry = self._get_subentry()
        subentry_data: dict[str, object] | None = dict(subentry.data) if subentry else None
        participants = self._get_participant_names()
        current_connection = (
            get_connection_target_name(subentry_data.get(CONF_CONNECTION))  # type: ignore[arg-type]  # stored subentry data always matches BatteryConfigSchema
            if subentry_data
            else None
        )
        default_name = await self._async_get_default_name(ELEMENT_TYPE)
        if not isinstance(current_connection, str):
            current_connection = participants[0] if participants else ""

        input_fields = get_input_fields(ELEMENT_TYPE)

        sections = self._get_sections()
        user_input = preprocess_sectioned_choose_input(user_input, input_fields, sections)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            self._step1_data = user_input
            # Check if partitions are enabled
            if _as_mapping(user_input.get(SECTION_PARTITIONING)).get(CONF_CONFIGURE_PARTITIONS):
                return await self.async_step_partitions()
            # No partitions - finalize directly
            config = self._build_config(user_input, {})
            return self._finalize(config)

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

    async def async_step_partitions(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle partition configuration step."""
        errors = self._validate_partition_input(user_input)
        subentry = self._get_subentry()
        subentry_data: dict[str, object] | None = dict(subentry.data) if subentry else None

        if user_input is not None and not errors:
            config = self._build_config(self._step1_data, user_input)
            return self._finalize(config)

        input_fields = get_input_fields(ELEMENT_TYPE)
        entity_metadata = extract_entity_metadata(self.hass, self._get_entry())
        section_inclusion_map = build_sectioned_inclusion_map(input_fields, entity_metadata)

        schema = self._build_partition_schema(input_fields, section_inclusion_map, subentry_data)
        defaults = user_input if user_input is not None else self._build_partition_defaults(input_fields, subentry_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="partitions", data_schema=schema, errors=errors)

    def _build_schema(
        self,
        participants: list[str],
        input_fields: InputFieldGroups,
        section_inclusion_map: dict[str, dict[str, list[str]]],
        current_connection: str | None = None,
        subentry_data: Mapping[str, object] | None = None,
    ) -> vol.Schema:
        """Build the schema with name, connection, and choose selectors for main inputs."""
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        surfaced_fields = get_surfaced_input_fields(ELEMENT_TYPE)
        element_name = _as_str(subentry_data.get(CONF_NAME)) if subentry_data else None
        surfaced_entries = build_surfaced_schema_entries(
            self.hass, self._get_entry(), element_name, SURFACED_PRICE_HINTS, surfaced_fields
        )
        return build_sectioned_choose_schema(
            self._get_sections(),
            input_fields,
            field_schema,
            section_inclusion_map,
            current_data=_sectioned_view(subentry_data),
            top_level_entries=build_common_fields(
                include_connection=True,
                participants=participants,
                current_connection=current_connection,
            ),
            extra_field_entries={
                SECTION_PARTITIONING: {
                    CONF_CONFIGURE_PARTITIONS: (
                        vol.Optional(CONF_CONFIGURE_PARTITIONS),
                        BooleanSelector(BooleanSelectorConfig()),
                    )
                },
                SECTION_PRICING: surfaced_entries,
            },
        )

    def _build_partition_schema(
        self,
        input_fields: InputFieldGroups,
        section_inclusion_map: dict[str, dict[str, list[str]]],
        subentry_data: Mapping[str, object] | None = None,
    ) -> vol.Schema:
        """Build the schema for partition fields."""
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        return build_sectioned_choose_schema(
            self._get_partition_sections(),
            input_fields,
            field_schema,
            section_inclusion_map,
            current_data=_sectioned_view(subentry_data),
        )

    def _build_defaults(
        self,
        default_name: str,
        input_fields: InputFieldGroups,
        subentry_data: Mapping[str, object] | None = None,
        connection_default: str | None = None,
    ) -> dict[str, object]:
        """Build default values for the main form."""
        connection_default = (
            connection_default
            if connection_default is not None
            else get_connection_target_name(subentry_data.get(CONF_CONNECTION))  # type: ignore[arg-type]  # stored subentry data always matches BatteryConfigSchema
            if subentry_data
            else None
        )
        # Check if partitions were previously configured
        has_partitions = False
        if subentry_data:
            for section_key in (SECTION_UNDERCHARGE, SECTION_OVERCHARGE):
                partition_section = _as_mapping(subentry_data.get(section_key))
                if any(partition_section.get(field_name) is not None for field_name in PARTITION_FIELD_NAMES):
                    has_partitions = True
                    break

        hub_entry = self._get_entry()
        element_name = _as_str(subentry_data.get(CONF_NAME)) if subentry_data else None
        surfaced_fields = get_surfaced_input_fields(ELEMENT_TYPE)
        surfaced_defaults = build_surfaced_defaults(hub_entry, element_name, SURFACED_PRICE_HINTS, surfaced_fields)

        section_defaults = build_sectioned_choose_defaults(
            self._get_sections(),
            input_fields,
            current_data=subentry_data,
            base_defaults={
                SECTION_PARTITIONING: {
                    CONF_CONFIGURE_PARTITIONS: has_partitions,
                },
                SECTION_PRICING: surfaced_defaults,
            },
        )
        return {
            CONF_NAME: default_name if subentry_data is None else subentry_data.get(CONF_NAME),
            CONF_CONNECTION: connection_default,
            **section_defaults,
        }

    def _build_partition_defaults(
        self,
        input_fields: InputFieldGroups,
        subentry_data: Mapping[str, object] | None = None,
    ) -> dict[str, dict[str, object]]:
        """Build default values for the partition form."""
        return build_sectioned_choose_defaults(
            self._get_partition_sections(),
            input_fields,
            current_data=subentry_data,
        )

    def _validate_user_input(
        self,
        user_input: dict[str, object] | None,
        input_fields: InputFieldGroups,
    ) -> dict[str, str] | None:
        """Validate user input and return errors dict if any."""
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        self._validate_name(_as_str(user_input.get(CONF_NAME)), errors)
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        errors.update(
            validate_sectioned_choose_fields(
                user_input,
                input_fields,
                field_schema,
                self._get_sections(),
                exclude_fields=(*PARTITION_FIELD_NAMES, *SURFACED_POLICY_FIELDS),
            )
        )
        return errors if errors else None

    def _validate_partition_input(self, user_input: object | None) -> dict[str, str] | None:
        """Validate partition input and return errors dict if any.

        All partition fields are optional, so no validation is needed.
        This method exists for consistency with the validation pattern and
        can be extended if required partition fields are added in the future.
        """
        if user_input is None:
            return None
        return None

    def _build_config(
        self,
        main_input: Mapping[str, object],
        partition_input: Mapping[str, object],
    ) -> dict[str, object]:
        """Build final config dict from user input."""
        input_fields = get_input_fields(ELEMENT_TYPE)
        sections = self._get_sections()
        config_dict = convert_sectioned_choose_data_to_config(
            main_input,
            input_fields,
            sections,
            exclude_fields=tuple(SURFACED_POLICY_FIELDS),
        )

        if partition_input:
            partition_sections = self._get_partition_sections()
            partition_config = convert_sectioned_choose_data_to_config(
                partition_input,
                input_fields,
                partition_sections,
            )
            for section_key in (SECTION_UNDERCHARGE, SECTION_OVERCHARGE):
                if section_key in partition_config:
                    config_dict[section_key] = partition_config[section_key]

        return {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE,
            CONF_NAME: main_input[CONF_NAME],
            CONF_CONNECTION: normalize_connection_target(main_input[CONF_CONNECTION]),  # type: ignore[arg-type]  # user input validated by choose selector against the connection schema
            **config_dict,
        }

    def _finalize(self, config: dict[str, object]) -> SubentryFlowResult:
        """Finalize the flow by creating or updating the entry and saving surfaced rules."""
        name = str(self._step1_data[CONF_NAME])

        # Save surfaced policy rules from the pricing section input
        pricing_input = _as_mapping(self._step1_data.get(SECTION_PRICING))
        hub_entry = self._get_entry()
        translations = self._surfaced_rule_translations(name)
        subentry = self._get_subentry()
        is_new = subentry is None
        save_surfaced_rules_from_input(
            self.hass,
            hub_entry,
            name,
            pricing_input,
            SURFACED_PRICE_HINTS,
            translations,
            apply_defaults=is_new,
        )

        if subentry is not None:
            return self.async_update_and_abort(self._get_entry(), subentry, title=name, data=config)
        return self.async_create_entry(title=name, data=config)

    def _surfaced_rule_translations(self, element_name: str) -> dict[str, str]:
        """Build translated rule names for surfaced policy rules."""
        return {
            "charge_cost": f"{element_name} charge cost",
            "discharge_cost": f"{element_name} discharge cost",
        }
