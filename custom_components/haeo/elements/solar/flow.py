"""Solar element configuration flows."""

from typing import Any, ClassVar, cast

from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult, UnknownSubEntry
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_inclusion_map, build_participant_selector
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

from .schema import CONF_CONNECTION, ELEMENT_TYPE, INPUT_FIELDS, SolarConfigSchema

# Keys to exclude when extracting entity selections
_EXCLUDE_KEYS = (CONF_NAME, CONF_CONNECTION)


class SolarSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle solar element configuration flows."""

    has_value_source_step: ClassVar[bool] = True

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        self._step1_data: dict[str, Any] = {}

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
        inclusion_map = build_inclusion_map(INPUT_FIELDS, entity_metadata)
        participants = self._get_participant_names()
        schema = self._build_step1_schema(
            participants,
            inclusion_map,
            current_connection,
        )
        defaults = user_input if user_input is not None else self._build_step1_defaults(default_name, subentry_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    def _build_step1_schema(
        self,
        participants: list[str],
        inclusion_map: dict[str, list[str]],
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

        for field_info in INPUT_FIELDS:
            include_entities = inclusion_map.get(field_info.field_name)
            marker, selector = build_entity_schema_entry(
                field_info,
                config_schema=SolarConfigSchema,
                include_entities=include_entities,
            )
            schema_dict[marker] = selector

        return vol.Schema(schema_dict)

    def _validate_user_input(self, user_input: dict[str, Any] | None) -> dict[str, str] | None:
        if user_input is None:
            return None
        errors: dict[str, str] = {}
        self._validate_name(user_input.get(CONF_NAME), errors)
        self._validate_entity_selections(user_input, errors)
        return errors if errors else None

    async def async_step_values(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 2: configurable value entry."""
        errors: dict[str, str] = {}
        subentry = self._get_subentry()
        current_data = dict(subentry.data) if subentry else None
        entity_selections = extract_entity_selections(self._step1_data, _EXCLUDE_KEYS)

        if user_input is not None and self._validate_configurable_values(entity_selections, user_input, errors):
            config = self._build_config(entity_selections, user_input, current_data)
            return self._finalize(config)

        schema = build_configurable_value_schema(INPUT_FIELDS, entity_selections, current_data)

        # Skip step 2 if no configurable fields need input
        if not schema.schema:
            configurable_values = get_configurable_value_defaults(INPUT_FIELDS, entity_selections, current_data)
            config = self._build_config(entity_selections, configurable_values, current_data)
            return self._finalize(config)

        defaults = get_configurable_value_defaults(INPUT_FIELDS, entity_selections, current_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(step_id="values", data_schema=schema, errors=errors)

    def _build_step1_defaults(self, default_name: str, subentry_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build default values for step 1 form.

        Uses the InputFieldDefaults.mode to determine pre-selection:
        - mode='value': Pre-select the configurable entity
        - mode='entity': Pre-select the specified entity
        - mode=None: No pre-selection (empty list)
        """
        configurable_entity_id = get_configurable_entity_id()

        if subentry_data is None:
            # First setup: pre-select configurable entity when defaults.mode == "value"
            defaults: dict[str, Any] = {}
            for field in INPUT_FIELDS:
                if field.defaults is not None and field.defaults.mode == "value":
                    defaults[field.field_name] = [configurable_entity_id]
                else:
                    defaults[field.field_name] = []
            defaults[CONF_NAME] = default_name
            defaults[CONF_CONNECTION] = None
            return defaults

        # Reconfigure: get entry/subentry IDs for resolving created entities
        subentry = self._get_subentry()
        entry = self._get_entry()
        entry_id = entry.entry_id
        subentry_id = subentry.subentry_id if subentry else ""

        entity_defaults: dict[str, Any] = {}
        for field in INPUT_FIELDS:
            value = subentry_data.get(field.field_name)
            if isinstance(value, list):
                # Entity link (multi-select): use stored entity IDs
                entity_defaults[field.field_name] = value
            elif isinstance(value, str):
                # Entity ID (single-select from v0.1.0): use as-is
                entity_defaults[field.field_name] = [value]
            elif isinstance(value, (float, int, bool)):
                # Scalar value: resolve to the HAEO-created entity
                resolved = resolve_configurable_entity_id(entry_id, subentry_id, field.field_name)
                entity_defaults[field.field_name] = [resolved or configurable_entity_id]
            else:
                # Field not in stored data: empty selection (user cleared it)
                entity_defaults[field.field_name] = []

        return {
            CONF_NAME: subentry_data.get(CONF_NAME),
            CONF_CONNECTION: subentry_data.get(CONF_CONNECTION),
            **entity_defaults,
        }

    def _build_config(
        self,
        entity_selections: dict[str, list[str]],
        configurable_values: dict[str, Any],
        current_data: dict[str, Any] | None = None,
    ) -> SolarConfigSchema:
        """Build final config dict from step data."""
        name = self._step1_data.get(CONF_NAME)
        connection = self._step1_data.get(CONF_CONNECTION)
        entry = self._get_entry()
        subentry = self._get_subentry()
        config_dict = convert_entity_selections_to_config(
            entity_selections,
            configurable_values,
            INPUT_FIELDS,
            current_data,
            entry_id=entry.entry_id,
            subentry_id=subentry.subentry_id if subentry else None,
        )
        return cast(
            "SolarConfigSchema",
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                CONF_CONNECTION: connection,
                **config_dict,
            },
        )

    def _finalize(self, config: SolarConfigSchema) -> SubentryFlowResult:
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
            is_optional = field_name in SolarConfigSchema.__optional_keys__

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
