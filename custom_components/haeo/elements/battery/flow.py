"""Battery element configuration flows."""

from typing import Any, cast

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.data.loader.extractors import EntityMetadata, extract_entity_metadata
from custom_components.haeo.flows.field_schema import (
    MODE_SUFFIX,
    InputMode,
    build_mode_schema_entry,
    build_value_schema_entry,
    get_mode_defaults,
    get_value_defaults,
)
from custom_components.haeo.schema.util import UnitSpec

from .schema import (
    CONF_CAPACITY,
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
    CONF_UNDERCHARGE_COST,
    CONF_UNDERCHARGE_PERCENTAGE,
    ELEMENT_TYPE,
    INPUT_FIELDS,
    BatteryConfigSchema,
)

# Unit specifications for entity filtering
POWER_UNITS: UnitSpec = UnitOfPower
ENERGY_UNITS: UnitSpec = UnitOfEnergy
PERCENTAGE_UNITS: list[UnitSpec] = ["%"]
PRICE_UNITS: list[UnitSpec] = [("*", "/", unit.value) for unit in UnitOfEnergy]


def _filter_incompatible_entities(
    entity_metadata: list[EntityMetadata],
    accepted_units: UnitSpec | list[UnitSpec],
) -> list[str]:
    """Return entity IDs that are NOT compatible with the accepted units."""
    return [v.entity_id for v in entity_metadata if not v.is_compatible_with(accepted_units)]


def _build_connection_selector(participants: list[str], current_value: str | None = None) -> vol.All:
    """Build a selector for choosing connection target from participants."""
    options_list = list(participants)
    if current_value and current_value not in options_list:
        options_list.append(current_value)

    options: list[SelectOptionDict] = [SelectOptionDict(value=p, label=p) for p in options_list]
    return vol.All(
        vol.Coerce(str),
        vol.Strip,
        vol.Length(min=1, msg="Element name cannot be empty"),
        SelectSelector(SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)),
    )


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
        vol.Required(CONF_CONNECTION): _build_connection_selector(participants, current_connection),
    }

    # Add mode selectors for all input fields
    for field_info in INPUT_FIELDS:
        marker, selector = build_mode_schema_entry(field_info)
        schema_dict[marker] = selector

    return vol.Schema(schema_dict)


def _build_step2_schema(
    mode_selections: dict[str, str],
    entity_metadata: list[EntityMetadata],
) -> vol.Schema:
    """Build the schema for step 2: value entry based on mode selections."""
    # Build exclusion lists for entity selectors
    incompatible_power = _filter_incompatible_entities(entity_metadata, POWER_UNITS)
    incompatible_energy = _filter_incompatible_entities(entity_metadata, ENERGY_UNITS)
    incompatible_percentage = _filter_incompatible_entities(entity_metadata, PERCENTAGE_UNITS)
    incompatible_price = _filter_incompatible_entities(entity_metadata, PRICE_UNITS)

    # Map field names to their exclusion lists
    exclusion_map: dict[str, list[str]] = {
        CONF_CAPACITY: incompatible_energy,
        CONF_INITIAL_CHARGE_PERCENTAGE: incompatible_percentage,
        CONF_MIN_CHARGE_PERCENTAGE: incompatible_percentage,
        CONF_MAX_CHARGE_PERCENTAGE: incompatible_percentage,
        CONF_EFFICIENCY: incompatible_percentage,
        CONF_MAX_CHARGE_POWER: incompatible_power,
        CONF_MAX_DISCHARGE_POWER: incompatible_power,
        CONF_EARLY_CHARGE_INCENTIVE: incompatible_price,
        CONF_DISCHARGE_COST: incompatible_price,
        CONF_UNDERCHARGE_PERCENTAGE: incompatible_percentage,
        CONF_OVERCHARGE_PERCENTAGE: incompatible_percentage,
        CONF_UNDERCHARGE_COST: incompatible_price,
        CONF_OVERCHARGE_COST: incompatible_price,
    }

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


class BatterySubentryFlowHandler(ConfigSubentryFlow):
    """Handle battery element configuration flows."""

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        # Store step 1 data for use in step 2
        self._step1_data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 1: name, connection, and mode selections."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors[CONF_NAME] = "missing_name"
            elif name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            if not errors:
                # Store step 1 data and proceed to step 2
                self._step1_data = user_input
                return await self.async_step_values()

        participants = self._get_participant_names()
        schema = _build_step1_schema(participants)

        # Apply default mode selections
        defaults = get_mode_defaults(INPUT_FIELDS)
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
            # Combine step 1 and step 2 data
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

            return self.async_create_entry(title=str(name), data=cast("BatteryConfigSchema", config))

        entity_metadata = extract_entity_metadata(self.hass)
        schema = _build_step2_schema(self._step1_data, entity_metadata)

        # Apply default values based on modes
        defaults = get_value_defaults(INPUT_FIELDS, self._step1_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="values",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 1 of reconfiguration: name, connection, and mode selections."""
        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors[CONF_NAME] = "missing_name"
            elif name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            if not errors:
                # Store step 1 data and proceed to step 2
                self._step1_data = user_input
                return await self.async_step_reconfigure_values()

        current_connection = subentry.data.get(CONF_CONNECTION)
        participants = self._get_participant_names()
        schema = _build_step1_schema(
            participants,
            current_connection=current_connection if isinstance(current_connection, str) else None,
        )

        # Get current values for pre-population
        current_data = dict(subentry.data)
        mode_defaults = get_mode_defaults(INPUT_FIELDS, current_data)
        defaults = {
            CONF_NAME: current_data.get(CONF_NAME),
            CONF_CONNECTION: current_data.get(CONF_CONNECTION),
            **mode_defaults,
        }
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure_values(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 2 of reconfiguration: value entry based on mode selections."""
        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            # Combine step 1 and step 2 data
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
                data=cast("BatteryConfigSchema", config),
            )

        entity_metadata = extract_entity_metadata(self.hass)
        schema = _build_step2_schema(self._step1_data, entity_metadata)

        # Get current values for pre-population
        current_data = dict(subentry.data)
        defaults = get_value_defaults(INPUT_FIELDS, self._step1_data, current_data)
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

    def _get_participant_names(self) -> list[str]:
        """Return element names available as connection targets."""
        from custom_components.haeo.const import CONF_ADVANCED_MODE  # noqa: PLC0415
        from custom_components.haeo.elements import ELEMENT_TYPES, ConnectivityLevel  # noqa: PLC0415

        hub_entry = self._get_entry()
        advanced_mode = hub_entry.data.get(CONF_ADVANCED_MODE, False)
        current_id = self._get_current_subentry_id()

        result: list[str] = []
        for subentry in hub_entry.subentries.values():
            if subentry.subentry_id == current_id:
                continue

            element_type = subentry.data.get(CONF_ELEMENT_TYPE)
            if element_type not in ELEMENT_TYPES:
                continue

            connectivity = ELEMENT_TYPES[element_type].connectivity
            if connectivity == ConnectivityLevel.ALWAYS.value or (
                connectivity == ConnectivityLevel.ADVANCED.value and advanced_mode
            ):
                result.append(subentry.title)

        return result

    def _get_current_subentry_id(self) -> str | None:
        """Return the active subentry ID when reconfiguring, otherwise None."""
        try:
            return self._get_reconfigure_subentry().subentry_id
        except Exception:
            return None
