"""Grid element configuration flows."""

from typing import Any, ClassVar, cast

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_exclusion_map, build_participant_selector
from custom_components.haeo.flows.field_schema import (
    MODE_SUFFIX,
    InputMode,
    build_mode_schema_entry,
    build_value_schema_entry,
    get_mode_defaults,
    get_value_defaults,
)

from .schema import CONF_CONNECTION, ELEMENT_TYPE, INPUT_FIELDS, GridConfigSchema


def _build_step1_schema(
    participants: list[str],
    current_connection: str | None = None,
) -> vol.Schema:
    """Build the schema for step 1: name, connection, and mode selections."""
    schema_dict: dict[vol.Marker, Any] = {
        # Name field
        vol.Required(CONF_NAME): vol.All(
            vol.Coerce(str),
            vol.Strip,
            vol.Length(min=1, msg="Name cannot be empty"),
            TextSelector(TextSelectorConfig()),
        ),
        # Connection field
        vol.Required(CONF_CONNECTION): build_participant_selector(participants, current_connection),
    }

    # Add mode selectors for all input fields
    for field_info in INPUT_FIELDS:
        marker, selector = build_mode_schema_entry(field_info, config_schema=GridConfigSchema)
        schema_dict[marker] = selector

    return vol.Schema(schema_dict)


def _build_step2_schema(
    mode_selections: dict[str, str],
    exclusion_map: dict[str, list[str]],
) -> vol.Schema:
    """Build the schema for step 2: value entry based on mode selections.

    Args:
        mode_selections: Mode selections from step 1 (field_name_mode -> mode value).
        exclusion_map: Field name -> list of incompatible entity IDs.

    Returns:
        Schema with value input fields based on selected modes.

    """
    schema_dict: dict[vol.Marker, Any] = {}

    for field_info in INPUT_FIELDS:
        mode_key = f"{field_info.field_name}{MODE_SUFFIX}"
        mode_str = mode_selections.get(mode_key, InputMode.NONE)
        mode = InputMode(mode_str) if mode_str else InputMode.NONE

        exclude_entities = exclusion_map.get(field_info.field_name, [])
        entry = build_value_schema_entry(field_info, mode, exclude_entities=exclude_entities)

        if entry is not None:
            marker, selector = entry
            schema_dict[marker] = selector

    return vol.Schema(schema_dict)


class GridSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle grid element configuration flows."""

    has_value_source_step: ClassVar[bool] = True

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        # Store step 1 data for use in step 2
        self._step1_data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 1: name, connection, and mode selection."""
        # Clear step 1 data at start to avoid stale state from incomplete flows
        if user_input is None:
            self._step1_data = {}

        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                # Store step 1 data and proceed to step 2
                self._step1_data = user_input
                return await self.async_step_values()

        participants = self._get_participant_names()
        schema = _build_step1_schema(participants)

        # Apply default mode selections
        defaults = get_mode_defaults(INPUT_FIELDS, GridConfigSchema)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_values(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 2: value entry based on mode selections."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = self._step1_data.get(CONF_NAME)
            connection = self._step1_data.get(CONF_CONNECTION)

            # Build final config from values
            config: dict[str, Any] = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                CONF_CONNECTION: connection,
                # Add values from step 2 (excluding mode fields which were in step 1)
                **{k: v for k, v in user_input.items() if not k.endswith(MODE_SUFFIX)},
            }

            return self.async_create_entry(title=str(name), data=cast("GridConfigSchema", config))

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        schema = _build_step2_schema(self._step1_data, exclusion_map)

        # Apply default values based on modes
        defaults = get_value_defaults(INPUT_FIELDS, self._step1_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="values",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step 1: name, connection, and mode selection."""
        # Clear step 1 data at start to avoid stale state from incomplete flows
        if user_input is None:
            self._step1_data = {}

        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                # Store step 1 data and proceed to step 2
                self._step1_data = user_input
                return await self.async_step_reconfigure_values()

        current_connection = subentry.data.get(CONF_CONNECTION)
        participants = self._get_participant_names()
        schema = _build_step1_schema(
            participants,
            current_connection=current_connection if isinstance(current_connection, str) else None,
        )

        # Apply current values plus inferred modes
        defaults = {
            CONF_NAME: subentry.data.get(CONF_NAME),
            CONF_CONNECTION: current_connection,
            **get_mode_defaults(INPUT_FIELDS, GridConfigSchema, dict(subentry.data)),
        }
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure_values(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfigure step 2: value entry based on mode selections."""
        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            name = self._step1_data.get(CONF_NAME)
            connection = self._step1_data.get(CONF_CONNECTION)

            # Build final config from values
            config: dict[str, Any] = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                CONF_CONNECTION: connection,
                # Add values from step 2 (excluding mode fields)
                **{k: v for k, v in user_input.items() if not k.endswith(MODE_SUFFIX)},
            }

            return self.async_update_and_abort(
                self._get_entry(),
                subentry,
                title=str(name),
                data=cast("GridConfigSchema", config),
            )

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        schema = _build_step2_schema(self._step1_data, exclusion_map)

        # Get current values for pre-population
        defaults = get_value_defaults(INPUT_FIELDS, self._step1_data, dict(subentry.data))
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="reconfigure_values",
            data_schema=schema,
            errors=errors,
        )
