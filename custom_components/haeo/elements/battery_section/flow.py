"""Battery section element configuration flows."""

from typing import Any, ClassVar, cast

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.data.loader.extractors import EntityMetadata, extract_entity_metadata
from custom_components.haeo.flows.constants import ensure_constant_entities_exist
from custom_components.haeo.flows.field_schema import (
    build_constant_value_schema,
    build_entity_selector_with_constant,
    convert_entity_selections_to_config,
    get_constant_value_defaults,
    get_entity_selection_defaults,
    has_constant_selection,
)
from custom_components.haeo.schema.util import UnitSpec

from .schema import CONF_CAPACITY, CONF_INITIAL_CHARGE, ELEMENT_TYPE, INPUT_FIELDS, BatterySectionConfigSchema

# Unit specifications
ENERGY_UNITS: UnitSpec = UnitOfEnergy


def _filter_incompatible_entities(
    entity_metadata: list[EntityMetadata],
    accepted_units: UnitSpec | list[UnitSpec],
) -> list[str]:
    """Return entity IDs that are NOT compatible with the accepted units."""
    return [v.entity_id for v in entity_metadata if not v.is_compatible_with(accepted_units)]


def _get_field(field_name: str) -> Any:
    """Get field info by name."""
    return next(f for f in INPUT_FIELDS if f.field_name == field_name)


def _build_step1_schema(entity_metadata: list[EntityMetadata]) -> vol.Schema:
    """Build the schema for step 1: name and entity selection."""
    incompatible_energy = _filter_incompatible_entities(entity_metadata, ENERGY_UNITS)

    return vol.Schema(
        {
            vol.Required(CONF_NAME): vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
            vol.Required(CONF_CAPACITY): build_entity_selector_with_constant(
                _get_field(CONF_CAPACITY),
                exclude_entities=incompatible_energy,
            ),
            vol.Required(CONF_INITIAL_CHARGE): build_entity_selector_with_constant(
                _get_field(CONF_INITIAL_CHARGE),
                exclude_entities=incompatible_energy,
            ),
        }
    )


class BatterySectionSubentryFlowHandler(ConfigSubentryFlow):
    """Handle battery section element configuration flows."""

    has_value_source_step: ClassVar[bool] = True

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        self._step1_data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 1: name and entity selection."""
        if user_input is None:
            self._step1_data = {}

        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors[CONF_NAME] = "missing_name"
            elif name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            # Validate required entity fields
            for field_name in (CONF_CAPACITY, CONF_INITIAL_CHARGE):
                if not user_input.get(field_name):
                    errors[field_name] = "required"

            if not errors:
                self._step1_data = user_input
                return await self.async_step_values()

        # Ensure constant entity exists before building schema
        ensure_constant_entities_exist(self.hass)

        entity_metadata = extract_entity_metadata(self.hass)
        schema = _build_step1_schema(entity_metadata)

        # Apply defaults
        defaults: dict[str, Any] = dict(get_entity_selection_defaults(INPUT_FIELDS, BatterySectionConfigSchema))
        defaults[CONF_NAME] = None
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_values(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 2: constant value entry for fields with haeo.constant."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = self._step1_data.get(CONF_NAME)

            entity_selections: dict[str, list[str]] = {}
            for k, v in self._step1_data.items():
                if k == CONF_NAME:
                    continue
                if isinstance(v, list):
                    entity_selections[k] = v

            config_dict = convert_entity_selections_to_config(entity_selections, user_input, INPUT_FIELDS)

            # Validate constant values were provided for required fields
            for field_info in INPUT_FIELDS:
                field_name = field_info.field_name
                if has_constant_selection(entity_selections.get(field_name, [])) and field_name not in user_input:
                    errors[field_name] = "required"

            if not errors:
                config: dict[str, Any] = {
                    CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                    CONF_NAME: name,
                    **config_dict,
                }
                return self.async_create_entry(title=name, data=cast("BatterySectionConfigSchema", config))

        entity_selections = {k: v for k, v in self._step1_data.items() if k != CONF_NAME and isinstance(v, list)}

        schema = build_constant_value_schema(INPUT_FIELDS, entity_selections)

        if not schema.schema:
            name = self._step1_data.get(CONF_NAME)
            config_dict = convert_entity_selections_to_config(entity_selections, {}, INPUT_FIELDS)
            config: dict[str, Any] = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                **config_dict,
            }
            return self.async_create_entry(title=name, data=cast("BatterySectionConfigSchema", config))

        defaults = get_constant_value_defaults(INPUT_FIELDS, entity_selections)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="values",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step 1: name and entity selection."""
        if user_input is None:
            self._step1_data = {}

        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors[CONF_NAME] = "missing_name"
            elif name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            for field_name in (CONF_CAPACITY, CONF_INITIAL_CHARGE):
                if not user_input.get(field_name):
                    errors[field_name] = "required"

            if not errors:
                self._step1_data = user_input
                return await self.async_step_reconfigure_values()

        ensure_constant_entities_exist(self.hass)

        entity_metadata = extract_entity_metadata(self.hass)
        schema = _build_step1_schema(entity_metadata)

        current_data = dict(subentry.data)
        entity_defaults = get_entity_selection_defaults(INPUT_FIELDS, BatterySectionConfigSchema, current_data)
        defaults: dict[str, Any] = dict(entity_defaults)
        defaults[CONF_NAME] = subentry.data.get(CONF_NAME)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure_values(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step 2: constant value entry."""
        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            name = self._step1_data.get(CONF_NAME)

            entity_selections: dict[str, list[str]] = {}
            for k, v in self._step1_data.items():
                if k == CONF_NAME:
                    continue
                if isinstance(v, list):
                    entity_selections[k] = v

            config_dict = convert_entity_selections_to_config(entity_selections, user_input, INPUT_FIELDS)

            for field_info in INPUT_FIELDS:
                field_name = field_info.field_name
                if has_constant_selection(entity_selections.get(field_name, [])) and field_name not in user_input:
                    errors[field_name] = "required"

            if not errors:
                config: dict[str, Any] = {
                    CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                    CONF_NAME: name,
                    **config_dict,
                }
                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    title=str(name),
                    data=cast("BatterySectionConfigSchema", config),
                )

        entity_selections = {k: v for k, v in self._step1_data.items() if k != CONF_NAME and isinstance(v, list)}

        schema = build_constant_value_schema(INPUT_FIELDS, entity_selections)

        if not schema.schema:
            name = self._step1_data.get(CONF_NAME)
            config_dict = convert_entity_selections_to_config(entity_selections, {}, INPUT_FIELDS)
            config: dict[str, Any] = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                **config_dict,
            }
            return self.async_update_and_abort(
                self._get_entry(),
                subentry,
                title=str(name),
                data=cast("BatterySectionConfigSchema", config),
            )

        defaults = get_constant_value_defaults(INPUT_FIELDS, entity_selections, dict(subentry.data))
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="reconfigure_values",
            data_schema=schema,
            errors=errors,
        )

    def _get_used_names(self) -> set[str]:
        """Return all configured element names excluding the current subentry."""
        current_id = self._get_current_subentry_id()
        return {
            subentry.title for subentry in self._get_entry().subentries.values() if subentry.subentry_id != current_id
        }

    def _get_current_subentry_id(self) -> str | None:
        """Return the active subentry ID when reconfiguring, otherwise None."""
        try:
            return self._get_reconfigure_subentry().subentry_id
        except Exception:
            return None
