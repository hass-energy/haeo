"""Battery element configuration flows."""

from typing import Any, ClassVar, Final, cast

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_exclusion_map, build_participant_selector
from custom_components.haeo.flows.field_schema import (
    MODE_SUFFIX,
    InputMode,
    build_mode_schema_entry,
    build_value_schema_entry,
    get_mode_defaults,
    get_value_defaults,
)
from custom_components.haeo.model.const import OutputType

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
    BatteryConfigSchema,
)

# Input field definitions for building config flow schemas
# These must match the definitions in BatteryAdapter.inputs()
INPUT_FIELDS: Final[tuple[InputFieldInfo[NumberEntityDescription], ...]] = (
    InputFieldInfo(
        field_name=CONF_CAPACITY,
        entity_description=NumberEntityDescription(
            key=CONF_CAPACITY,
            translation_key=f"{ELEMENT_TYPE}_{CONF_CAPACITY}",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=NumberDeviceClass.ENERGY_STORAGE,
            native_min_value=0.1,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type=OutputType.ENERGY,
        time_series=True,
        boundaries=True,
    ),
    InputFieldInfo(
        field_name=CONF_INITIAL_CHARGE_PERCENTAGE,
        entity_description=NumberEntityDescription(
            key=CONF_INITIAL_CHARGE_PERCENTAGE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_INITIAL_CHARGE_PERCENTAGE}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.BATTERY,
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=0.1,
        ),
        output_type=OutputType.STATE_OF_CHARGE,
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_MIN_CHARGE_PERCENTAGE,
        entity_description=NumberEntityDescription(
            key=CONF_MIN_CHARGE_PERCENTAGE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_MIN_CHARGE_PERCENTAGE}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.BATTERY,
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=1.0,
        ),
        output_type=OutputType.STATE_OF_CHARGE,
        time_series=True,
        boundaries=True,
        default=0.0,
    ),
    InputFieldInfo(
        field_name=CONF_MAX_CHARGE_PERCENTAGE,
        entity_description=NumberEntityDescription(
            key=CONF_MAX_CHARGE_PERCENTAGE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_CHARGE_PERCENTAGE}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.BATTERY,
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=1.0,
        ),
        output_type=OutputType.STATE_OF_CHARGE,
        time_series=True,
        boundaries=True,
        default=100.0,
    ),
    InputFieldInfo(
        field_name=CONF_EFFICIENCY,
        entity_description=NumberEntityDescription(
            key=CONF_EFFICIENCY,
            translation_key=f"{ELEMENT_TYPE}_{CONF_EFFICIENCY}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.POWER_FACTOR,
            native_min_value=50.0,
            native_max_value=100.0,
            native_step=0.1,
        ),
        output_type=OutputType.EFFICIENCY,
        time_series=True,
        default=99.0,
    ),
    InputFieldInfo(
        field_name=CONF_MAX_CHARGE_POWER,
        entity_description=NumberEntityDescription(
            key=CONF_MAX_CHARGE_POWER,
            translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_CHARGE_POWER}",
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=NumberDeviceClass.POWER,
            native_min_value=0.0,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type=OutputType.POWER,
        direction="+",
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_MAX_DISCHARGE_POWER,
        entity_description=NumberEntityDescription(
            key=CONF_MAX_DISCHARGE_POWER,
            translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_DISCHARGE_POWER}",
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=NumberDeviceClass.POWER,
            native_min_value=0.0,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type=OutputType.POWER,
        direction="-",
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_EARLY_CHARGE_INCENTIVE,
        entity_description=NumberEntityDescription(
            key=CONF_EARLY_CHARGE_INCENTIVE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_EARLY_CHARGE_INCENTIVE}",
            native_min_value=0.0,
            native_max_value=1.0,
            native_step=0.001,
        ),
        output_type=OutputType.PRICE,
        direction="-",
        time_series=True,
        default=0.001,
    ),
    InputFieldInfo(
        field_name=CONF_DISCHARGE_COST,
        entity_description=NumberEntityDescription(
            key=CONF_DISCHARGE_COST,
            translation_key=f"{ELEMENT_TYPE}_{CONF_DISCHARGE_COST}",
            native_min_value=0.0,
            native_max_value=1.0,
            native_step=0.001,
        ),
        output_type=OutputType.PRICE,
        direction="-",
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_UNDERCHARGE_PERCENTAGE,
        entity_description=NumberEntityDescription(
            key=CONF_UNDERCHARGE_PERCENTAGE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_UNDERCHARGE_PERCENTAGE}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.BATTERY,
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=1.0,
        ),
        output_type=OutputType.STATE_OF_CHARGE,
        time_series=True,
        boundaries=True,
        device_name="battery_device_undercharge",
    ),
    InputFieldInfo(
        field_name=CONF_OVERCHARGE_PERCENTAGE,
        entity_description=NumberEntityDescription(
            key=CONF_OVERCHARGE_PERCENTAGE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_OVERCHARGE_PERCENTAGE}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.BATTERY,
            native_min_value=0.0,
            native_max_value=100.0,
            native_step=1.0,
        ),
        output_type=OutputType.STATE_OF_CHARGE,
        time_series=True,
        boundaries=True,
        device_name="battery_device_overcharge",
    ),
    InputFieldInfo(
        field_name=CONF_UNDERCHARGE_COST,
        entity_description=NumberEntityDescription(
            key=CONF_UNDERCHARGE_COST,
            translation_key=f"{ELEMENT_TYPE}_{CONF_UNDERCHARGE_COST}",
            native_min_value=0.0,
            native_max_value=10.0,
            native_step=0.001,
        ),
        output_type=OutputType.PRICE,
        direction="-",
        time_series=True,
        device_name="battery_device_undercharge",
    ),
    InputFieldInfo(
        field_name=CONF_OVERCHARGE_COST,
        entity_description=NumberEntityDescription(
            key=CONF_OVERCHARGE_COST,
            translation_key=f"{ELEMENT_TYPE}_{CONF_OVERCHARGE_COST}",
            native_min_value=0.0,
            native_max_value=10.0,
            native_step=0.001,
        ),
        output_type=OutputType.PRICE,
        direction="-",
        time_series=True,
        device_name="battery_device_overcharge",
    ),
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
        vol.Required(CONF_CONNECTION): build_participant_selector(participants, current_connection),
    }

    # Add mode selectors for all input fields
    for field_info in INPUT_FIELDS:
        marker, selector = build_mode_schema_entry(field_info, config_schema=BatteryConfigSchema)
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


class BatterySubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle battery element configuration flows."""

    has_value_source_step: ClassVar[bool] = True

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        # Store step 1 data for use in step 2
        self._step1_data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle step 1: name, connection, and mode selections."""
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
        defaults = get_mode_defaults(INPUT_FIELDS, BatteryConfigSchema)
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
        """Handle step 1 of reconfiguration: name, connection, and mode selections."""
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

        # Get current values for pre-population
        current_data = dict(subentry.data)
        mode_defaults = get_mode_defaults(INPUT_FIELDS, BatteryConfigSchema, current_data)
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
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        schema = _build_step2_schema(self._step1_data, exclusion_map)

        # Get current values for pre-population
        current_data = dict(subentry.data)
        defaults = get_value_defaults(INPUT_FIELDS, self._step1_data, current_data)
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="reconfigure_values",
            data_schema=schema,
            errors=errors,
        )
