"""Battery element configuration flows."""

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult, UnknownSubEntry
from homeassistant.helpers.selector import BooleanSelector, BooleanSelectorConfig
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.elements import get_input_field_schema_info, is_element_config_schema
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
from custom_components.haeo.schema import (
    as_constant_value,
    extract_entity_ids,
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
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    build_common_fields,
    build_efficiency_fields,
    build_power_limits_fields,
    build_pricing_fields,
    common_section,
    efficiency_section,
    power_limits_section,
    pricing_section,
)

from .adapter import adapter
from .schema import (
    CONF_CAPACITY,
    CONF_CONFIGURE_PARTITIONS,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_PARTITION_COST,
    CONF_PARTITION_PERCENTAGE,
    ELEMENT_TYPE,
    PARTITION_FIELD_NAMES,
    SECTION_LIMITS,
    SECTION_OVERCHARGE,
    SECTION_PARTITIONING,
    SECTION_STORAGE,
    SECTION_UNDERCHARGE,
    BatteryConfigSchema,
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


class BatterySubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle battery element configuration flows."""

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        self._step1_data: dict[str, Any] = {}

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
            pricing_section((CONF_PRICE_SOURCE_TARGET, CONF_PRICE_TARGET_SOURCE), collapsed=False),
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
            element_config: BatteryConfigSchema = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                SECTION_COMMON: {
                    CONF_NAME: default_name,
                    CONF_CONNECTION: normalize_connection_target(current_connection),
                },
                SECTION_STORAGE: {
                    CONF_CAPACITY: as_constant_value(0.0),
                    CONF_INITIAL_CHARGE_PERCENTAGE: as_constant_value(0.0),
                },
                SECTION_LIMITS: {},
                SECTION_POWER_LIMITS: {},
                SECTION_PRICING: {},
                SECTION_EFFICIENCY: {},
                SECTION_PARTITIONING: {},
            }

        input_fields = adapter.inputs(element_config)

        sections = self._get_sections()
        user_input = preprocess_sectioned_choose_input(user_input, input_fields, sections)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            self._step1_data = user_input
            # Check if partitions are enabled
            if user_input.get(SECTION_PARTITIONING, {}).get(CONF_CONFIGURE_PARTITIONS):
                return await self.async_step_partitions()
            # No partitions - finalize directly
            config = self._build_config(user_input, {})
            return self._finalize(config)

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

    async def async_step_partitions(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle partition configuration step."""
        errors = self._validate_partition_input(user_input)
        subentry = self._get_subentry()
        subentry_data = dict(subentry.data) if subentry else None

        if user_input is not None and not errors:
            config = self._build_config(self._step1_data, user_input)
            return self._finalize(config)

        input_fields = adapter.inputs(subentry_data)
        entity_metadata = extract_entity_metadata(self.hass)
        section_inclusion_map = build_sectioned_inclusion_map(input_fields, entity_metadata)

        schema = self._build_partition_schema(section_inclusion_map, subentry_data)
        defaults = user_input if user_input is not None else self._build_partition_defaults(subentry_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="partitions", data_schema=schema, errors=errors)

    def _build_schema(
        self,
        participants: list[str],
        input_fields: InputFieldGroups,
        section_inclusion_map: dict[str, dict[str, list[str]]],
        current_connection: str | None = None,
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema with name, connection, and choose selectors for main inputs."""
        sections = self._get_sections()
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        field_entries: dict[str, dict[str, tuple[vol.Marker, Any]]] = {
            SECTION_COMMON: build_common_fields(
                include_connection=True,
                participants=participants,
                current_connection=current_connection,
            ),
            SECTION_PARTITIONING: {
                CONF_CONFIGURE_PARTITIONS: (
                    vol.Optional(CONF_CONFIGURE_PARTITIONS),
                    BooleanSelector(BooleanSelectorConfig()),
                ),
            },
        }

        section_builders = {
            SECTION_EFFICIENCY: build_efficiency_fields,
            SECTION_POWER_LIMITS: build_power_limits_fields,
            SECTION_PRICING: build_pricing_fields,
        }

        for section_def in sections:
            section_fields = input_fields.get(section_def.key, {})
            if not section_fields:
                continue
            field_entries.setdefault(section_def.key, {}).update(
                section_builders.get(section_def.key, build_choose_field_entries)(
                    section_fields,
                    field_schema=field_schema.get(section_def.key, {}),
                    inclusion_map=section_inclusion_map.get(section_def.key, {}),
                    current_data=subentry_data.get(section_def.key) if subentry_data else None,
                )
            )

        return vol.Schema(build_section_schema(sections, field_entries))

    def _build_partition_schema(
        self,
        section_inclusion_map: dict[str, dict[str, list[str]]],
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema for partition fields."""
        sections = self._get_partition_sections()
        input_fields = adapter.inputs(subentry_data)
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        field_entries: dict[str, dict[str, tuple[vol.Marker, Any]]] = {}

        for section_def in sections:
            section_fields = input_fields.get(section_def.key, {})
            if not section_fields:
                continue
            field_entries[section_def.key] = build_choose_field_entries(
                section_fields,
                field_schema=field_schema.get(section_def.key, {}),
                inclusion_map=section_inclusion_map.get(section_def.key, {}),
                current_data=subentry_data.get(section_def.key) if subentry_data else None,
            )

        return vol.Schema(build_section_schema(sections, field_entries))

    def _build_defaults(
        self,
        default_name: str,
        subentry_data: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build default values for the main form."""
        common_data = subentry_data.get(SECTION_COMMON, {}) if subentry_data else {}
        defaults: dict[str, Any] = {
            SECTION_COMMON: {
                CONF_NAME: default_name if subentry_data is None else common_data.get(CONF_NAME),
                CONF_CONNECTION: get_connection_target_name(common_data.get(CONF_CONNECTION)) if subentry_data else None,
            },
            SECTION_STORAGE: {},
            SECTION_LIMITS: {},
            SECTION_POWER_LIMITS: {},
            SECTION_PRICING: {},
            SECTION_EFFICIENCY: {},
            SECTION_PARTITIONING: {},
        }

        input_fields = adapter.inputs(subentry_data)
        for section_key, section_fields in input_fields.items():
            if section_key in (SECTION_UNDERCHARGE, SECTION_OVERCHARGE):
                continue
            for field_info in section_fields.values():
                choose_default = get_choose_default(
                    field_info,
                    subentry_data.get(section_key) if subentry_data else None,
                )
                if choose_default is not None:
                    defaults.setdefault(section_key, {})[field_info.field_name] = choose_default

        # Check if partitions were previously configured
        has_partitions = False
        if subentry_data:
            for section_key in (SECTION_UNDERCHARGE, SECTION_OVERCHARGE):
                if any(
                    subentry_data.get(section_key, {}).get(field_name) is not None
                    for field_name in PARTITION_FIELD_NAMES
                ):
                    has_partitions = True
                    break
        defaults[SECTION_PARTITIONING][CONF_CONFIGURE_PARTITIONS] = has_partitions

        return defaults

    def _build_partition_defaults(self, subentry_data: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Build default values for the partition form."""
        defaults: dict[str, Any] = {
            SECTION_UNDERCHARGE: {},
            SECTION_OVERCHARGE: {},
        }
        input_fields = adapter.inputs(subentry_data)
        for section_key in (SECTION_UNDERCHARGE, SECTION_OVERCHARGE):
            section_fields = input_fields.get(section_key, {})
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
        field_schema = get_input_field_schema_info(ELEMENT_TYPE, input_fields)
        errors.update(
            validate_sectioned_choose_fields(
                user_input,
                input_fields,
                field_schema,
                self._get_sections(),
                exclude_fields=tuple(PARTITION_FIELD_NAMES),
            )
        )
        return errors if errors else None

    def _validate_partition_input(self, user_input: dict[str, Any] | None) -> dict[str, str] | None:
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
        main_input: dict[str, Any],
        partition_input: dict[str, Any],
    ) -> dict[str, Any]:
        """Build final config dict from user input."""
        input_fields = adapter.inputs(main_input)
        sections = self._get_sections()
        config_dict = convert_sectioned_choose_data_to_config(
            main_input,
            input_fields,
            sections,
        )

        common_config = config_dict.get(SECTION_COMMON, {})
        if CONF_CONNECTION in common_config:
            common_config[CONF_CONNECTION] = normalize_connection_target(common_config[CONF_CONNECTION])

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
            **config_dict,
        }

    def _finalize(self, config: dict[str, Any]) -> SubentryFlowResult:
        """Finalize the flow by creating or updating the entry."""
        name = str(self._step1_data.get(SECTION_COMMON, {}).get(CONF_NAME))
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
