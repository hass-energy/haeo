"""Battery element configuration flows."""

from typing import Any, ClassVar, Final, cast

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
)
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

from .schema import (
    CONF_CONNECTION,
    CONF_PARTITIONS,
    ELEMENT_TYPE,
    INPUT_FIELDS,
    BatteryConfigSchema,
    PartitionConfigSchema,
)

# Maximum number of configurable partitions
MAX_PARTITIONS: Final = 5

# Configuration key for partition count
CONF_PARTITION_COUNT: Final = "partition_count"


def _build_step1_schema(
    participants: list[str],
    current_connection: str | None = None,
    current_partition_count: int = 0,
) -> vol.Schema:
    """Build the schema for step 1: name, connection, partition count, and mode selections."""
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
        # Partition count selector (0 = legacy mode, 1-5 = partition mode)
        vol.Optional(CONF_PARTITION_COUNT, default=current_partition_count): NumberSelector(
            NumberSelectorConfig(min=0, max=MAX_PARTITIONS, step=1, mode=NumberSelectorMode.BOX)
        ),
    }

    # Add mode selectors for all input fields
    for field_info in INPUT_FIELDS:
        marker, selector = build_mode_schema_entry(field_info, config_schema=BatteryConfigSchema)
        schema_dict[marker] = selector

    return vol.Schema(schema_dict)


def _build_step2_schema(
    mode_selections: dict[str, str],
    exclusion_map: dict[str, list[str]],
    partition_count: int = 0,
) -> vol.Schema:
    """Build the schema for step 2: value entry based on mode selections.

    Args:
        mode_selections: Mode selections from step 1 (field_name_mode -> mode value).
        exclusion_map: Field name -> list of incompatible entity IDs.
        partition_count: Number of partitions to configure (0 = legacy mode).

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

    # Add partition configuration fields if partition_count > 0
    if partition_count > 0:
        for i in range(partition_count):
            partition_prefix = f"partition_{i}_"
            # Partition name
            schema_dict[vol.Required(f"{partition_prefix}name")] = TextSelector(TextSelectorConfig())
            # Partition capacity (kWh)
            schema_dict[vol.Required(f"{partition_prefix}capacity")] = NumberSelector(
                NumberSelectorConfig(min=0.1, max=1000, step=0.1, mode=NumberSelectorMode.BOX, unit_of_measurement="kWh")
            )
            # Optional partition costs ($/kWh)
            schema_dict[vol.Optional(f"{partition_prefix}charge_cost")] = NumberSelector(
                NumberSelectorConfig(min=0, max=10, step=0.001, mode=NumberSelectorMode.BOX, unit_of_measurement="$/kWh")
            )
            schema_dict[vol.Optional(f"{partition_prefix}discharge_cost")] = NumberSelector(
                NumberSelectorConfig(min=0, max=10, step=0.001, mode=NumberSelectorMode.BOX, unit_of_measurement="$/kWh")
            )

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
        partition_count = int(self._step1_data.get(CONF_PARTITION_COUNT, 0))

        if user_input is not None:
            # Combine step 1 and step 2 data
            name = self._step1_data.get(CONF_NAME)
            connection = self._step1_data.get(CONF_CONNECTION)

            # Build final config from values (excluding mode and partition_* fields)
            config: dict[str, Any] = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                CONF_CONNECTION: connection,
            }

            # Add non-mode, non-partition values
            for k, v in user_input.items():
                if not k.endswith(MODE_SUFFIX) and not k.startswith("partition_"):
                    config[k] = v

            # Extract partition data if partition mode is enabled
            if partition_count > 0:
                partitions: list[PartitionConfigSchema] = []
                for i in range(partition_count):
                    prefix = f"partition_{i}_"
                    partition: PartitionConfigSchema = {
                        "name": user_input.get(f"{prefix}name", f"Partition {i + 1}"),
                        "capacity": float(user_input.get(f"{prefix}capacity", 0)),
                    }
                    # Add optional costs if provided
                    charge_cost = user_input.get(f"{prefix}charge_cost")
                    if charge_cost is not None:
                        partition["charge_cost"] = float(charge_cost)
                    discharge_cost = user_input.get(f"{prefix}discharge_cost")
                    if discharge_cost is not None:
                        partition["discharge_cost"] = float(discharge_cost)
                    partitions.append(partition)
                config[CONF_PARTITIONS] = partitions

            return self.async_create_entry(title=str(name), data=cast("BatteryConfigSchema", config))

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        schema = _build_step2_schema(self._step1_data, exclusion_map, partition_count)

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
        current_partitions = subentry.data.get(CONF_PARTITIONS, [])
        current_partition_count = len(current_partitions) if isinstance(current_partitions, list) else 0

        participants = self._get_participant_names()
        schema = _build_step1_schema(
            participants,
            current_connection=current_connection if isinstance(current_connection, str) else None,
            current_partition_count=current_partition_count,
        )

        # Get current values for pre-population
        current_data = dict(subentry.data)
        mode_defaults = get_mode_defaults(INPUT_FIELDS, BatteryConfigSchema, current_data)
        defaults = {
            CONF_NAME: current_data.get(CONF_NAME),
            CONF_CONNECTION: current_data.get(CONF_CONNECTION),
            CONF_PARTITION_COUNT: current_partition_count,
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
        partition_count = int(self._step1_data.get(CONF_PARTITION_COUNT, 0))

        if user_input is not None:
            # Combine step 1 and step 2 data
            name = self._step1_data.get(CONF_NAME)
            connection = self._step1_data.get(CONF_CONNECTION)

            # Build final config from values (excluding mode and partition_* fields)
            config: dict[str, Any] = {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                CONF_NAME: name,
                CONF_CONNECTION: connection,
            }

            # Add non-mode, non-partition values
            for k, v in user_input.items():
                if not k.endswith(MODE_SUFFIX) and not k.startswith("partition_"):
                    config[k] = v

            # Extract partition data if partition mode is enabled
            if partition_count > 0:
                partitions: list[PartitionConfigSchema] = []
                for i in range(partition_count):
                    prefix = f"partition_{i}_"
                    partition: PartitionConfigSchema = {
                        "name": user_input.get(f"{prefix}name", f"Partition {i + 1}"),
                        "capacity": float(user_input.get(f"{prefix}capacity", 0)),
                    }
                    # Add optional costs if provided
                    charge_cost = user_input.get(f"{prefix}charge_cost")
                    if charge_cost is not None:
                        partition["charge_cost"] = float(charge_cost)
                    discharge_cost = user_input.get(f"{prefix}discharge_cost")
                    if discharge_cost is not None:
                        partition["discharge_cost"] = float(discharge_cost)
                    partitions.append(partition)
                config[CONF_PARTITIONS] = partitions

            return self.async_update_and_abort(
                self._get_entry(),
                subentry,
                title=str(name),
                data=cast("BatteryConfigSchema", config),
            )

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        schema = _build_step2_schema(self._step1_data, exclusion_map, partition_count)

        # Get current values for pre-population (including existing partition data)
        current_data = dict(subentry.data)
        defaults = get_value_defaults(INPUT_FIELDS, self._step1_data, current_data)

        # Pre-populate existing partition values
        current_partitions = current_data.get(CONF_PARTITIONS, [])
        if isinstance(current_partitions, list):
            for i, partition in enumerate(current_partitions):
                if i < partition_count and isinstance(partition, dict):
                    prefix = f"partition_{i}_"
                    if "name" in partition:
                        defaults[f"{prefix}name"] = partition["name"]
                    if "capacity" in partition:
                        defaults[f"{prefix}capacity"] = partition["capacity"]
                    if "charge_cost" in partition:
                        defaults[f"{prefix}charge_cost"] = partition["charge_cost"]
                    if "discharge_cost" in partition:
                        defaults[f"{prefix}discharge_cost"] = partition["discharge_cost"]

        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="reconfigure_values",
            data_schema=schema,
            errors=errors,
        )
