"""Battery element configuration flows."""

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult, UnknownSubEntry
from homeassistant.helpers.selector import BooleanSelector, BooleanSelectorConfig, TextSelector, TextSelectorConfig
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
    convert_sectioned_choose_data_to_config,
    get_choose_default,
    preprocess_sectioned_choose_input,
    validate_sectioned_choose_fields,
)

from .adapter import adapter
from .schema import (
    CONF_CAPACITY,
    CONF_CONFIGURE_PARTITIONS,
    CONF_CONNECTION,
    CONF_DISCHARGE_COST,
    CONF_EARLY_CHARGE_INCENTIVE,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_OVERCHARGE_COST,
    CONF_OVERCHARGE_PERCENTAGE,
    CONF_SECTION_ADVANCED,
    CONF_SECTION_BASIC,
    CONF_SECTION_LIMITS,
    CONF_SECTION_OVERCHARGE,
    CONF_SECTION_UNDERCHARGE,
    CONF_UNDERCHARGE_COST,
    CONF_UNDERCHARGE_PERCENTAGE,
    ELEMENT_TYPE,
    OPTIONAL_INPUT_FIELDS,
    PARTITION_FIELD_NAMES,
    BatteryConfigSchema,
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
            SectionDefinition(
                key=CONF_SECTION_BASIC,
                fields=(
                    CONF_NAME,
                    CONF_CONNECTION,
                    CONF_CAPACITY,
                    CONF_INITIAL_CHARGE_PERCENTAGE,
                ),
                collapsed=False,
            ),
            SectionDefinition(
                key=CONF_SECTION_LIMITS,
                fields=(
                    CONF_MIN_CHARGE_PERCENTAGE,
                    CONF_MAX_CHARGE_PERCENTAGE,
                    CONF_MAX_CHARGE_POWER,
                    CONF_MAX_DISCHARGE_POWER,
                ),
                collapsed=False,
            ),
            SectionDefinition(
                key=CONF_SECTION_ADVANCED,
                fields=(
                    CONF_EFFICIENCY,
                    CONF_EARLY_CHARGE_INCENTIVE,
                    CONF_DISCHARGE_COST,
                    CONF_CONFIGURE_PARTITIONS,
                ),
                collapsed=True,
            ),
        )

    def _get_partition_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the partition configuration step."""
        return (
            SectionDefinition(
                key=CONF_SECTION_UNDERCHARGE,
                fields=(CONF_UNDERCHARGE_PERCENTAGE, CONF_UNDERCHARGE_COST),
                collapsed=False,
            ),
            SectionDefinition(
                key=CONF_SECTION_OVERCHARGE,
                fields=(CONF_OVERCHARGE_PERCENTAGE, CONF_OVERCHARGE_COST),
                collapsed=False,
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
        current_connection = subentry_data.get(CONF_SECTION_BASIC, {}).get(CONF_CONNECTION) if subentry_data else None

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
                CONF_SECTION_BASIC: {
                    CONF_NAME: default_name,
                    CONF_CONNECTION: current_connection,
                    CONF_CAPACITY: 0.0,
                    CONF_INITIAL_CHARGE_PERCENTAGE: 0.0,
                },
                CONF_SECTION_LIMITS: {},
                CONF_SECTION_ADVANCED: {},
            }

        input_fields = adapter.inputs(element_config)

        sections = self._get_sections()
        user_input = preprocess_sectioned_choose_input(user_input, input_fields, sections)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            self._step1_data = user_input
            # Check if partitions are enabled
            if user_input.get(CONF_SECTION_ADVANCED, {}).get(CONF_CONFIGURE_PARTITIONS):
                return await self.async_step_partitions()
            # No partitions - finalize directly
            config = self._build_config(user_input, {})
            return self._finalize(config)

        entity_metadata = extract_entity_metadata(self.hass)
        # Only include main input fields (not partition fields) in step 1
        main_fields = {name: info for name, info in input_fields.items() if name not in PARTITION_FIELD_NAMES}
        inclusion_map = build_inclusion_map(main_fields, entity_metadata)
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

    async def async_step_partitions(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle partition configuration step."""
        errors = self._validate_partition_input(user_input)
        subentry = self._get_subentry()
        subentry_data = dict(subentry.data) if subentry else None

        if user_input is not None and not errors:
            config = self._build_config(self._step1_data, user_input)
            return self._finalize(config)

        input_fields = adapter.inputs(subentry_data)
        partition_fields = {name: info for name, info in input_fields.items() if name in PARTITION_FIELD_NAMES}
        entity_metadata = extract_entity_metadata(self.hass)
        inclusion_map = build_inclusion_map(partition_fields, entity_metadata)

        schema = self._build_partition_schema(inclusion_map, subentry_data)
        defaults = user_input if user_input is not None else self._build_partition_defaults(subentry_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="partitions", data_schema=schema, errors=errors)

    def _build_schema(
        self,
        participants: list[str],
        input_fields: Mapping[str, InputFieldInfo[Any]],
        inclusion_map: dict[str, list[str]],
        current_connection: str | None = None,
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema with name, connection, and choose selectors for main inputs."""
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
            CONF_CONFIGURE_PARTITIONS: (
                vol.Optional(CONF_CONFIGURE_PARTITIONS),
                BooleanSelector(BooleanSelectorConfig()),
            ),
        }

        main_fields = {name: info for name, info in input_fields.items() if name not in PARTITION_FIELD_NAMES}
        field_entries.update(
            build_choose_field_entries(
                main_fields,
                optional_fields=OPTIONAL_INPUT_FIELDS,
                inclusion_map=inclusion_map,
                current_data=subentry_data,
            )
        )

        return vol.Schema(build_section_schema(sections, field_entries))

    def _build_partition_schema(
        self,
        inclusion_map: dict[str, list[str]],
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema for partition fields."""
        sections = self._get_partition_sections()
        field_entries: dict[str, tuple[vol.Marker, Any]] = {}
        input_fields = adapter.inputs(subentry_data)
        partition_fields = {name: info for name, info in input_fields.items() if name in PARTITION_FIELD_NAMES}

        field_entries.update(
            build_choose_field_entries(
                partition_fields,
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
        """Build default values for the main form."""
        basic_data = subentry_data.get(CONF_SECTION_BASIC, {}) if subentry_data else {}
        defaults: dict[str, Any] = {
            CONF_SECTION_BASIC: {
                CONF_NAME: default_name if subentry_data is None else basic_data.get(CONF_NAME),
                CONF_CONNECTION: basic_data.get(CONF_CONNECTION) if subentry_data else None,
            },
            CONF_SECTION_LIMITS: {},
            CONF_SECTION_ADVANCED: {},
        }

        input_fields = adapter.inputs(subentry_data)
        section_map = {field_name: section.key for section in self._get_sections() for field_name in section.fields}
        for field_info in input_fields.values():
            if field_info.field_name in PARTITION_FIELD_NAMES:
                continue
            choose_default = get_choose_default(field_info, subentry_data)
            if choose_default is not None:
                section_key = section_map.get(field_info.field_name)
                if section_key:
                    defaults.setdefault(section_key, {})[field_info.field_name] = choose_default

        # Check if partitions were previously configured
        has_partitions = False
        if subentry_data:
            for section_key in (CONF_SECTION_UNDERCHARGE, CONF_SECTION_OVERCHARGE):
                if any(
                    subentry_data.get(section_key, {}).get(field_name) is not None
                    for field_name in PARTITION_FIELD_NAMES
                ):
                    has_partitions = True
                    break
        defaults[CONF_SECTION_ADVANCED][CONF_CONFIGURE_PARTITIONS] = has_partitions

        return defaults

    def _build_partition_defaults(self, subentry_data: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Build default values for the partition form."""
        defaults: dict[str, Any] = {
            CONF_SECTION_UNDERCHARGE: {},
            CONF_SECTION_OVERCHARGE: {},
        }
        input_fields = adapter.inputs(subentry_data)
        partition_fields = {name: info for name, info in input_fields.items() if name in PARTITION_FIELD_NAMES}
        section_map = {
            field_name: section.key for section in self._get_partition_sections() for field_name in section.fields
        }

        for field_info in partition_fields.values():
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

        if partition_input:
            partition_sections = self._get_partition_sections()
            partition_config = convert_sectioned_choose_data_to_config(
                partition_input,
                input_fields,
                partition_sections,
            )
            for section_key in (CONF_SECTION_UNDERCHARGE, CONF_SECTION_OVERCHARGE):
                if section_key in partition_config:
                    config_dict[section_key] = partition_config[section_key]

        return {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE,
            **config_dict,
        }

    def _finalize(self, config: dict[str, Any]) -> SubentryFlowResult:
        """Finalize the flow by creating or updating the entry."""
        name = str(self._step1_data.get(CONF_SECTION_BASIC, {}).get(CONF_NAME))
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
