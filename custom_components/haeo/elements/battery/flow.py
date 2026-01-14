"""Battery element configuration flows."""

from typing import Any, cast

from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult, UnknownSubEntry
from homeassistant.helpers.selector import BooleanSelector, BooleanSelectorConfig, TextSelector, TextSelectorConfig
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_inclusion_map, build_participant_selector
from custom_components.haeo.flows.field_schema import (
    build_choose_schema_entry,
    convert_choose_data_to_config,
    get_choose_default,
)

from .schema import (
    CONF_CONFIGURE_PARTITIONS,
    CONF_CONNECTION,
    ELEMENT_TYPE,
    INPUT_FIELDS,
    PARTITION_FIELD_NAMES,
    PARTITION_FIELDS,
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
        errors = self._validate_user_input(user_input)
        subentry = self._get_subentry()
        subentry_data = dict(subentry.data) if subentry else None

        if user_input is not None and not errors:
            self._step1_data = user_input
            # Check if partitions are enabled
            if user_input.get(CONF_CONFIGURE_PARTITIONS):
                return await self.async_step_partitions()
            # No partitions - finalize directly
            config = self._build_config(user_input, {})
            return self._finalize(config)

        translations = await async_get_translations(
            self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
        )
        default_name = translations[f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title"]

        current_connection = subentry_data.get(CONF_CONNECTION) if subentry_data else None
        entity_metadata = extract_entity_metadata(self.hass)
        # Only include main input fields (not partition fields) in step 1
        main_fields = tuple(f for f in INPUT_FIELDS if f.field_name not in PARTITION_FIELD_NAMES)
        inclusion_map = build_inclusion_map(main_fields, entity_metadata)
        participants = self._get_participant_names()

        schema = self._build_schema(participants, inclusion_map, current_connection)
        defaults = user_input if user_input is not None else self._build_defaults(default_name, subentry_data)
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

        entity_metadata = extract_entity_metadata(self.hass)
        inclusion_map = build_inclusion_map(PARTITION_FIELDS, entity_metadata)

        schema = self._build_partition_schema(inclusion_map)
        defaults = user_input if user_input is not None else self._build_partition_defaults(subentry_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="partitions", data_schema=schema, errors=errors)

    def _build_schema(
        self,
        participants: list[str],
        inclusion_map: dict[str, list[str]],
        current_connection: str | None = None,
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
        for field_info in INPUT_FIELDS:
            if field_info.field_name in PARTITION_FIELD_NAMES:
                continue
            is_optional = field_info.field_name in BatteryConfigSchema.__optional_keys__
            include_entities = inclusion_map.get(field_info.field_name)
            marker, selector = build_choose_schema_entry(
                field_info,
                is_optional=is_optional,
                include_entities=include_entities,
            )
            schema_dict[marker] = selector

        # Add checkbox for partition configuration at the end
        schema_dict[vol.Optional(CONF_CONFIGURE_PARTITIONS)] = BooleanSelector(BooleanSelectorConfig())

        return vol.Schema(schema_dict)

    def _build_partition_schema(self, inclusion_map: dict[str, list[str]]) -> vol.Schema:
        """Build the schema for partition fields."""
        schema_dict: dict[vol.Marker, Any] = {}

        for field_info in PARTITION_FIELDS:
            is_optional = field_info.field_name in BatteryConfigSchema.__optional_keys__
            include_entities = inclusion_map.get(field_info.field_name)
            marker, selector = build_choose_schema_entry(
                field_info,
                is_optional=is_optional,
                include_entities=include_entities,
            )
            schema_dict[marker] = selector

        return vol.Schema(schema_dict)

    def _build_defaults(self, default_name: str, subentry_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build default values for the main form."""
        defaults: dict[str, Any] = {
            CONF_NAME: default_name if subentry_data is None else subentry_data.get(CONF_NAME),
            CONF_CONNECTION: subentry_data.get(CONF_CONNECTION) if subentry_data else None,
        }

        entry_id: str | None = None
        subentry_id: str | None = None
        if subentry_data is not None:
            entry = self._get_entry()
            subentry = self._get_subentry()
            entry_id = entry.entry_id
            subentry_id = subentry.subentry_id if subentry else None

        # Only include main input fields (not partition fields)
        for field_info in INPUT_FIELDS:
            if field_info.field_name in PARTITION_FIELD_NAMES:
                continue
            choose_default = get_choose_default(
                field_info,
                current_data=subentry_data,
                entry_id=entry_id,
                subentry_id=subentry_id,
            )
            if choose_default is not None:
                defaults[field_info.field_name] = choose_default

        # Check if partitions were previously configured
        has_partitions = (
            any(subentry_data.get(fn) is not None for fn in PARTITION_FIELD_NAMES) if subentry_data else False
        )
        defaults[CONF_CONFIGURE_PARTITIONS] = has_partitions

        return defaults

    def _build_partition_defaults(self, subentry_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build default values for the partition form."""
        defaults: dict[str, Any] = {}

        entry_id: str | None = None
        subentry_id: str | None = None
        if subentry_data is not None:
            entry = self._get_entry()
            subentry = self._get_subentry()
            entry_id = entry.entry_id
            subentry_id = subentry.subentry_id if subentry else None

        for field_info in PARTITION_FIELDS:
            choose_default = get_choose_default(
                field_info,
                current_data=subentry_data,
                entry_id=entry_id,
                subentry_id=subentry_id,
            )
            if choose_default is not None:
                defaults[field_info.field_name] = choose_default

        return defaults

    def _validate_user_input(self, user_input: dict[str, Any] | None) -> dict[str, str] | None:
        """Validate user input and return errors dict if any."""
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        self._validate_name(user_input.get(CONF_NAME), errors)
        self._validate_choose_fields(user_input, errors, exclude_partition=True)
        return errors if errors else None

    def _validate_partition_input(self, user_input: dict[str, Any] | None) -> dict[str, str] | None:
        """Validate partition input and return errors dict if any."""
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        self._validate_partition_fields(user_input, errors)
        return errors if errors else None

    def _validate_choose_fields(
        self, user_input: dict[str, Any], errors: dict[str, str], *, exclude_partition: bool = False
    ) -> None:
        """Validate that required choose fields have valid selections."""
        for field_info in INPUT_FIELDS:
            field_name = field_info.field_name
            if exclude_partition and field_name in PARTITION_FIELD_NAMES:
                continue
            is_optional = field_name in BatteryConfigSchema.__optional_keys__

            if is_optional:
                continue

            value = user_input.get(field_name)
            if not self._is_valid_choose_value(value):
                errors[field_name] = "required"

    def _validate_partition_fields(self, user_input: dict[str, Any], errors: dict[str, str]) -> None:
        """Validate that required partition fields have valid selections."""
        for field_info in PARTITION_FIELDS:
            field_name = field_info.field_name
            is_optional = field_name in BatteryConfigSchema.__optional_keys__

            if is_optional:
                continue

            value = user_input.get(field_name)
            if not self._is_valid_choose_value(value):
                errors[field_name] = "required"

    def _is_valid_choose_value(self, value: Any) -> bool:
        """Check if a choose selector value is valid (has a selection)."""
        if not isinstance(value, dict):
            return False
        choice = value.get("choice")
        inner_value = value.get("value")
        if choice == "constant":
            return inner_value is not None
        if choice == "entity":
            return bool(inner_value)
        return False

    def _build_config(
        self,
        main_input: dict[str, Any],
        partition_input: dict[str, Any],
    ) -> BatteryConfigSchema:
        """Build final config dict from user input."""
        name = main_input.get(CONF_NAME)
        connection = main_input.get(CONF_CONNECTION)

        # Convert main fields (excluding partition field names)
        main_fields = tuple(f for f in INPUT_FIELDS if f.field_name not in PARTITION_FIELD_NAMES)
        config_dict = convert_choose_data_to_config(main_input, main_fields, _EXCLUDE_KEYS)

        # Convert partition fields if present
        if partition_input:
            partition_config = convert_choose_data_to_config(partition_input, PARTITION_FIELDS, ())
            config_dict.update(partition_config)

        return cast(
            "BatteryConfigSchema",
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                CONF_CONNECTION: connection,
                **config_dict,
            },
        )

    def _finalize(self, config: BatteryConfigSchema) -> SubentryFlowResult:
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
