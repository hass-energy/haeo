"""Battery element configuration flows."""

from collections.abc import Sequence
from typing import Any, ClassVar, cast

from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult, UnknownSubEntry
from homeassistant.helpers.selector import BooleanSelector, BooleanSelectorConfig, TextSelector, TextSelectorConfig
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_exclusion_map, build_participant_selector
from custom_components.haeo.flows.field_schema import (
    build_configurable_value_schema,
    build_entity_schema_entry,
    convert_entity_selections_to_config,
    extract_entity_selections,
    get_configurable_entity_id,
    get_configurable_value_defaults,
    has_configurable_selection,
    resolve_configurable_entity_id,
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

# Keys to exclude when extracting entity selections
_EXCLUDE_KEYS = (CONF_NAME, CONF_CONNECTION, CONF_CONFIGURE_PARTITIONS)


class BatterySubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle battery element configuration flows."""

    has_value_source_step: ClassVar[bool] = True

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        self._step1_data: dict[str, Any] = {}
        self._step2_data: dict[str, Any] = {}
        self._partition_entity_selections: dict[str, list[str]] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 1: name, connection, and entity selection."""
        return await self._async_step1(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step 1: name, connection, and entity selection."""
        return await self._async_step1(user_input)

    async def _async_step1(self, user_input: dict[str, Any] | None) -> SubentryFlowResult:
        """Shared logic for step 1: name, connection, and entity selection."""
        errors = self._validate_user_input(user_input)
        subentry = self._get_subentry()
        subentry_data = dict(subentry.data) if subentry else None

        if user_input is not None and not errors:
            self._step1_data = user_input
            return await self.async_step_values()

        translations = await async_get_translations(
            self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
        )
        default_name = translations[f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title"]

        current_connection = subentry_data.get(CONF_CONNECTION) if subentry_data else None
        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        participants = self._get_participant_names()
        schema = self._build_step1_schema(
            participants,
            exclusion_map,
            current_connection,
        )
        defaults = user_input if user_input is not None else self._build_step1_defaults(default_name, subentry_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    def _build_step1_schema(
        self,
        participants: list[str],
        exclusion_map: dict[str, list[str]],
        current_connection: str | None = None,
    ) -> vol.Schema:
        """Build the schema for step 1: name, connection, and entity selections."""
        schema_dict: dict[vol.Marker, Any] = {
            vol.Required(CONF_NAME): vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
            vol.Required(CONF_CONNECTION): build_participant_selector(participants, current_connection),
        }

        # Only include main input fields (not partition fields) in step 1
        for field_info in INPUT_FIELDS:
            if field_info.field_name in PARTITION_FIELD_NAMES:
                continue
            exclude_entities = exclusion_map.get(field_info.field_name, [])
            marker, selector = build_entity_schema_entry(
                field_info,
                config_schema=BatteryConfigSchema,
                exclude_entities=exclude_entities,
            )
            schema_dict[marker] = selector

        # Add checkbox for partition configuration at the end
        schema_dict[vol.Optional(CONF_CONFIGURE_PARTITIONS)] = BooleanSelector(BooleanSelectorConfig())

        return vol.Schema(schema_dict)

    def _validate_user_input(self, user_input: dict[str, Any] | None) -> dict[str, str] | None:
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        self._validate_name(user_input.get(CONF_NAME), errors)
        self._validate_entity_selections(user_input, errors)
        return errors if errors else None

    async def async_step_values(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 2: configurable value entry for main fields."""
        errors: dict[str, str] = {}
        subentry = self._get_subentry()
        current_data = dict(subentry.data) if subentry else None
        entity_selections = extract_entity_selections(self._step1_data, _EXCLUDE_KEYS)

        if user_input is not None and self._validate_configurable_values(entity_selections, user_input, errors):
            self._step2_data = user_input
            # Check if partitions are enabled
            if self._step1_data.get(CONF_CONFIGURE_PARTITIONS):
                return await self.async_step_partitions()
            # No partitions - finalize
            config = self._build_config(entity_selections, user_input, current_data, {}, {})
            return self._finalize(config)

        schema = build_configurable_value_schema(INPUT_FIELDS, entity_selections, current_data)

        # Skip step 2 if no configurable fields need input
        if not schema.schema:
            configurable_values = get_configurable_value_defaults(INPUT_FIELDS, entity_selections, current_data)
            self._step2_data = configurable_values
            # Check if partitions are enabled
            if self._step1_data.get(CONF_CONFIGURE_PARTITIONS):
                return await self.async_step_partitions()
            # No partitions - finalize
            config = self._build_config(entity_selections, configurable_values, current_data, {}, {})
            return self._finalize(config)

        defaults = get_configurable_value_defaults(INPUT_FIELDS, entity_selections, current_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="values", data_schema=schema, errors=errors)

    async def async_step_partitions(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 3: partition entity selection."""
        errors: dict[str, str] = {}
        subentry = self._get_subentry()
        current_data = dict(subentry.data) if subentry else None

        if user_input is not None and not errors:
            self._partition_entity_selections = extract_entity_selections(user_input, ())
            return await self.async_step_partition_values()

        # Build schema for partition entity selection
        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(PARTITION_FIELDS, entity_metadata)

        schema_dict: dict[vol.Marker, Any] = {}
        for field_info in PARTITION_FIELDS:
            exclude_entities = exclusion_map.get(field_info.field_name, [])
            marker, selector = build_entity_schema_entry(
                field_info,
                config_schema=BatteryConfigSchema,
                exclude_entities=exclude_entities,
            )
            schema_dict[marker] = selector

        schema = vol.Schema(schema_dict)
        defaults = self._build_partition_defaults(current_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="partitions", data_schema=schema, errors=errors)

    async def async_step_partition_values(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 4: configurable value entry for partition fields."""
        errors: dict[str, str] = {}
        subentry = self._get_subentry()
        current_data = dict(subentry.data) if subentry else None

        if user_input is not None and self._validate_partition_values(
            self._partition_entity_selections, user_input, errors
        ):
            main_entity_selections = extract_entity_selections(self._step1_data, _EXCLUDE_KEYS)
            config = self._build_config(
                main_entity_selections,
                self._step2_data,
                current_data,
                self._partition_entity_selections,
                user_input,
            )
            return self._finalize(config)

        schema = build_configurable_value_schema(PARTITION_FIELDS, self._partition_entity_selections, current_data)

        # Skip step 4 if no configurable fields need input
        if not schema.schema:
            configurable_values = get_configurable_value_defaults(
                PARTITION_FIELDS, self._partition_entity_selections, current_data
            )
            main_entity_selections = extract_entity_selections(self._step1_data, _EXCLUDE_KEYS)
            config = self._build_config(
                main_entity_selections,
                self._step2_data,
                current_data,
                self._partition_entity_selections,
                configurable_values,
            )
            return self._finalize(config)

        defaults = get_configurable_value_defaults(PARTITION_FIELDS, self._partition_entity_selections, current_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="partition_values", data_schema=schema, errors=errors)

    def _build_field_entity_defaults(
        self,
        fields: Sequence[Any],
        subentry_data: dict[str, Any] | None,
        entry_id: str,
        subentry_id: str,
    ) -> dict[str, list[str]]:
        """Build entity selection defaults for a list of fields.

        Uses the InputFieldDefaults.mode to determine pre-selection:
        - mode='value': Pre-select the configurable entity
        - mode='entity': Pre-select the specified entity
        - mode=None: No pre-selection (empty list)

        For reconfigure, entity links are preserved and scalar values resolve
        to created HAEO entities.
        """
        configurable_entity_id = get_configurable_entity_id()
        defaults: dict[str, list[str]] = {}

        for field in fields:
            value = subentry_data.get(field.field_name) if subentry_data else None

            if isinstance(value, list):
                # Entity link (multi-select): use stored entity IDs
                defaults[field.field_name] = value
            elif isinstance(value, str):
                # Entity ID (single-select from v0.1.0): use as-is
                defaults[field.field_name] = [value]
            elif isinstance(value, (float, int, bool)):
                # Scalar value: resolve to the HAEO-created entity
                resolved = resolve_configurable_entity_id(entry_id, subentry_id, field.field_name)
                defaults[field.field_name] = [resolved or configurable_entity_id]
            elif field.defaults is not None and field.defaults.mode == "value":
                # Field not in stored data or first setup: use defaults.mode
                defaults[field.field_name] = [configurable_entity_id]
            elif field.defaults is not None and field.defaults.mode == "entity" and field.defaults.entity:
                defaults[field.field_name] = [field.defaults.entity]
            else:
                defaults[field.field_name] = []

        return defaults

    def _build_partition_defaults(self, subentry_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build default values for partition form."""
        subentry = self._get_subentry()
        entry = self._get_entry()
        entry_id = entry.entry_id
        subentry_id = subentry.subentry_id if subentry else ""

        return self._build_field_entity_defaults(PARTITION_FIELDS, subentry_data, entry_id, subentry_id)

    def _build_step1_defaults(self, default_name: str, subentry_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build default values for step 1 form."""
        subentry = self._get_subentry()
        entry = self._get_entry()
        entry_id = entry.entry_id
        subentry_id = subentry.subentry_id if subentry else ""

        # Filter out partition fields for step 1
        step1_fields = [f for f in INPUT_FIELDS if f.field_name not in PARTITION_FIELD_NAMES]
        entity_defaults = self._build_field_entity_defaults(step1_fields, subentry_data, entry_id, subentry_id)

        # Check if partitions were previously configured
        has_partitions = (
            any(subentry_data.get(fn) is not None for fn in PARTITION_FIELD_NAMES) if subentry_data else False
        )

        return {
            CONF_NAME: subentry_data.get(CONF_NAME) if subentry_data else default_name,
            CONF_CONNECTION: subentry_data.get(CONF_CONNECTION) if subentry_data else None,
            CONF_CONFIGURE_PARTITIONS: has_partitions,
            **entity_defaults,
        }

    def _build_config(
        self,
        entity_selections: dict[str, list[str]],
        configurable_values: dict[str, Any],
        current_data: dict[str, Any] | None,
        partition_entity_selections: dict[str, list[str]],
        partition_configurable_values: dict[str, Any],
    ) -> BatteryConfigSchema:
        """Build final config dict from step data."""
        name = self._step1_data.get(CONF_NAME)
        connection = self._step1_data.get(CONF_CONNECTION)
        entry = self._get_entry()
        subentry = self._get_subentry()
        entry_id = entry.entry_id
        subentry_id = subentry.subentry_id if subentry else None

        # Main fields
        config_dict = convert_entity_selections_to_config(
            entity_selections,
            configurable_values,
            INPUT_FIELDS,
            current_data,
            entry_id=entry_id,
            subentry_id=subentry_id,
        )

        # Partition fields (only if enabled)
        if self._step1_data.get(CONF_CONFIGURE_PARTITIONS):
            partition_config = convert_entity_selections_to_config(
                partition_entity_selections,
                partition_configurable_values,
                PARTITION_FIELDS,
                current_data,
                entry_id=entry_id,
                subentry_id=subentry_id,
            )
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
        try:
            return self._get_reconfigure_subentry()
        except (ValueError, UnknownSubEntry):
            return None

    def _validate_entity_selections(self, user_input: dict[str, Any], errors: dict[str, str]) -> bool:
        """Validate that required entity fields have at least one selection."""
        for field_info in INPUT_FIELDS:
            field_name = field_info.field_name
            entities = user_input.get(field_name, [])
            is_optional = field_name in BatteryConfigSchema.__optional_keys__

            if not is_optional and not entities:
                errors[field_name] = "required"

        return not errors

    def _validate_configurable_values(
        self,
        entity_selections: dict[str, list[str]],
        user_input: dict[str, Any],
        errors: dict[str, str],
    ) -> bool:
        """Validate that configurable values were provided where needed.

        Step 2 values are always required when configurable entity is selected.
        """
        for field_info in INPUT_FIELDS:
            field_name = field_info.field_name
            is_configurable = has_configurable_selection(entity_selections.get(field_name, []))
            is_missing = field_name not in user_input
            # Always require a value when configurable is selected
            if is_configurable and is_missing:
                errors[field_name] = "required"

        return not errors

    def _validate_partition_values(
        self,
        entity_selections: dict[str, list[str]],
        configurable_values: dict[str, Any],
        errors: dict[str, str],
    ) -> bool:
        """Validate partition field values."""
        for field_info in PARTITION_FIELDS:
            field_name = field_info.field_name
            is_configurable = has_configurable_selection(entity_selections.get(field_name, []))
            is_missing = field_name not in configurable_values
            if is_configurable and is_missing:
                errors[field_name] = "required"

        return not errors
