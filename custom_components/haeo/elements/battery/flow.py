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
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_inclusion_map, build_participant_selector
from custom_components.haeo.flows.field_schema import (
    build_choose_schema_entry,
    convert_choose_data_to_config,
    get_choose_default,
    get_preferred_choice,
    preprocess_choose_selector_input,
    validate_choose_fields,
)

from .adapter import adapter
from .schema import (
    CONF_CAPACITY,
    CONF_CONFIGURE_PARTITIONS,
    CONF_CONNECTION,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    ELEMENT_TYPE,
    PARTITION_FIELD_NAMES,
    BatteryConfigSchema,
)

# Keys to exclude when converting choose data to config
_EXCLUDE_KEYS = (CONF_NAME, CONF_CONNECTION, CONF_CONFIGURE_PARTITIONS)


class BatterySubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle battery element configuration flows."""

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        self._step1_data: dict[str, Any] = {}

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
        current_connection = subentry_data.get(CONF_CONNECTION) if subentry_data else None

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
                CONF_NAME: default_name,
                CONF_CONNECTION: current_connection,
                CONF_CAPACITY: 0.0,
                CONF_INITIAL_CHARGE_PERCENTAGE: 0.0,
            }

        input_fields = adapter.inputs(element_config)

        user_input = preprocess_choose_selector_input(user_input, input_fields)
        errors = self._validate_user_input(user_input, input_fields)

        if user_input is not None and not errors:
            self._step1_data = user_input
            # Check if partitions are enabled
            if user_input.get(CONF_CONFIGURE_PARTITIONS):
                return await self.async_step_partitions()
            # No partitions - finalize directly
            config = self._build_config(user_input, {})
            return self._finalize(config)

        entity_metadata = extract_entity_metadata(self.hass)
        # Only include main input fields (not partition fields) in step 1
        main_fields = tuple(f for f in input_fields if f.field_name not in PARTITION_FIELD_NAMES)
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

        input_fields = adapter.inputs({})
        partition_fields = tuple(field for field in input_fields if field.field_name in PARTITION_FIELD_NAMES)
        entity_metadata = extract_entity_metadata(self.hass)
        inclusion_map = build_inclusion_map(partition_fields, entity_metadata)

        schema = self._build_partition_schema(inclusion_map, subentry_data)
        defaults = user_input if user_input is not None else self._build_partition_defaults(subentry_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="partitions", data_schema=schema, errors=errors)

    def _build_schema(
        self,
        participants: list[str],
        input_fields: tuple[Any, ...],
        inclusion_map: dict[str, list[str]],
        current_connection: str | None = None,
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema with name, connection, and choose selectors for main inputs."""
        schema_dict: dict[vol.Marker, Any] = {
            vol.Required(CONF_NAME): vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
            vol.Required(CONF_CONNECTION): build_participant_selector(participants, current_connection),
        }

        # Only include main input fields (not partition fields)
        for field_info in input_fields:
            if field_info.field_name in PARTITION_FIELD_NAMES:
                continue
            is_optional = (
                field_info.field_name in BatteryConfigSchema.__optional_keys__ and not field_info.force_required
            )
            include_entities = inclusion_map.get(field_info.field_name)
            preferred = get_preferred_choice(field_info, subentry_data, is_optional=is_optional)
            marker, selector = build_choose_schema_entry(
                field_info,
                is_optional=is_optional,
                include_entities=include_entities,
                preferred_choice=preferred,
            )
            schema_dict[marker] = selector

        # Add checkbox for partition configuration at the end
        schema_dict[vol.Optional(CONF_CONFIGURE_PARTITIONS)] = BooleanSelector(BooleanSelectorConfig())

        return vol.Schema(schema_dict)

    def _build_partition_schema(
        self,
        inclusion_map: dict[str, list[str]],
        subentry_data: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the schema for partition fields."""
        schema_dict: dict[vol.Marker, Any] = {}
        input_fields = adapter.inputs({})
        partition_fields = tuple(field for field in input_fields if field.field_name in PARTITION_FIELD_NAMES)

        for field_info in partition_fields:
            is_optional = (
                field_info.field_name in BatteryConfigSchema.__optional_keys__ and not field_info.force_required
            )
            include_entities = inclusion_map.get(field_info.field_name)
            preferred = get_preferred_choice(field_info, subentry_data, is_optional=is_optional)
            marker, selector = build_choose_schema_entry(
                field_info,
                is_optional=is_optional,
                include_entities=include_entities,
                preferred_choice=preferred,
            )
            schema_dict[marker] = selector

        return vol.Schema(schema_dict)

    def _build_defaults(
        self,
        default_name: str,
        subentry_data: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build default values for the main form."""
        defaults: dict[str, Any] = {
            CONF_NAME: default_name if subentry_data is None else subentry_data.get(CONF_NAME),
            CONF_CONNECTION: subentry_data.get(CONF_CONNECTION) if subentry_data else None,
        }

        # Only include main input fields (not partition fields)
        input_fields = adapter.inputs({})
        for field_info in input_fields:
            if field_info.field_name in PARTITION_FIELD_NAMES:
                continue
            choose_default = get_choose_default(field_info, subentry_data)
            if choose_default is not None:
                defaults[field_info.field_name] = choose_default

        # Check if partitions were previously configured
        has_partitions = (
            any(subentry_data.get(fn) is not None for fn in PARTITION_FIELD_NAMES) if subentry_data else False
        )
        defaults[CONF_CONFIGURE_PARTITIONS] = has_partitions

        return defaults

    def _build_partition_defaults(self, subentry_data: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Build default values for the partition form."""
        defaults: dict[str, Any] = {}
        input_fields = adapter.inputs({})
        partition_fields = tuple(field for field in input_fields if field.field_name in PARTITION_FIELD_NAMES)

        for field_info in partition_fields:
            choose_default = get_choose_default(field_info, subentry_data)
            if choose_default is not None:
                defaults[field_info.field_name] = choose_default

        return defaults

    def _validate_user_input(
        self,
        user_input: dict[str, Any] | None,
        input_fields: tuple[Any, ...],
    ) -> dict[str, str] | None:
        """Validate user input and return errors dict if any."""
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        self._validate_name(user_input.get(CONF_NAME), errors)
        errors.update(
            validate_choose_fields(
                user_input,
                input_fields,
                BatteryConfigSchema.__optional_keys__,
                exclude_fields=PARTITION_FIELD_NAMES,
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
        name = main_input.get(CONF_NAME)
        connection = main_input.get(CONF_CONNECTION)
        capacity = main_input.get(CONF_CAPACITY)
        initial_charge = main_input.get(CONF_INITIAL_CHARGE_PERCENTAGE)
        if not isinstance(name, str) or not isinstance(connection, str):
            msg = "Battery config missing name or connection"
            raise TypeError(msg)
        if not isinstance(capacity, (str, float, int, list)) or not isinstance(initial_charge, (str, float, int, list)):
            msg = "Battery config missing capacity values"
            raise TypeError(msg)
        input_fields = adapter.inputs(
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                CONF_CONNECTION: connection,
                CONF_CAPACITY: capacity,
                CONF_INITIAL_CHARGE_PERCENTAGE: initial_charge,
            }
        )

        # Convert main fields (excluding partition field names)
        main_fields = tuple(f for f in input_fields if f.field_name not in PARTITION_FIELD_NAMES)
        config_dict = convert_choose_data_to_config(main_input, main_fields, _EXCLUDE_KEYS)

        # Convert partition fields if present
        if partition_input:
            partition_fields = tuple(field for field in input_fields if field.field_name in PARTITION_FIELD_NAMES)
            partition_config = convert_choose_data_to_config(partition_input, partition_fields, ())
            config_dict.update(partition_config)

        return {
            CONF_ELEMENT_TYPE: ELEMENT_TYPE,
            CONF_NAME: name,
            CONF_CONNECTION: connection,
            **config_dict,
        }

    def _finalize(self, config: dict[str, Any]) -> SubentryFlowResult:
        """Finalize the flow by creating or updating the entry."""
        name = str(self._step1_data.get(CONF_NAME))
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
