"""HAEO element registry with explicit per-element adapters.

This module provides a centralized registry for all element types and their adapters.
The adapter layer transforms configuration elements into model elements and maps
model outputs to user-friendly device outputs.

Adapter Pattern:
    Configuration Element (with entity IDs) →
    Input entity values →
    Coordinator merges loaded values →
    Adapter.model_elements() →
    Model Elements (pure optimization) →
    Model.optimize() →
    Model Outputs (element-agnostic) →
    Adapter.outputs() →
    Device Outputs (user-friendly sensors)

Sub-element Naming Convention:
    Adapters may create multiple model elements and devices from a single config element.
    Sub-elements follow the pattern: {main_element}:{subname}
    Example: Battery "home_battery" creates:
        - "home_battery" (battery device)
        - "home_battery:connection" (implicit connection to network)
"""

from collections.abc import Mapping
import logging
import types
from typing import (
    Any,
    Final,
    Literal,
    NamedTuple,
    NotRequired,
    Protocol,
    Required,
    TypeAliasType,
    TypeGuard,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    runtime_checkable,
)

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import (
    CONF_ELEMENT_TYPE,
    ELEMENT_TYPE_NETWORK,
    NETWORK_OUTPUT_NAMES,
    ConnectivityLevel,
    NetworkDeviceName,
    NetworkOutputName,
)
from custom_components.haeo.model import ModelElementConfig, ModelOutputName
from custom_components.haeo.model.output_data import ModelOutputValue, OutputData

from . import battery, battery_section, connection, grid, inverter, load, node, solar
from .field_schema import FieldSchemaInfo
from .input_fields import InputFieldGroups, InputFieldInfo, InputFieldPath, InputFieldSection

_LOGGER = logging.getLogger(__name__)

type ElementType = Literal[
    "battery",
    "battery_section",
    "connection",
    "solar",
    "grid",
    "inverter",
    "load",
    "node",
]

ELEMENT_TYPE_INVERTER: Final = inverter.ELEMENT_TYPE
ELEMENT_TYPE_BATTERY: Final = battery.ELEMENT_TYPE
ELEMENT_TYPE_BATTERY_SECTION: Final = battery_section.ELEMENT_TYPE
ELEMENT_TYPE_CONNECTION: Final = connection.ELEMENT_TYPE
ELEMENT_TYPE_SOLAR: Final = solar.ELEMENT_TYPE
ELEMENT_TYPE_GRID: Final = grid.ELEMENT_TYPE
ELEMENT_TYPE_LOAD: Final = load.ELEMENT_TYPE
ELEMENT_TYPE_NODE: Final = node.ELEMENT_TYPE

ElementConfigSchema = (
    inverter.InverterConfigSchema
    | battery.BatteryConfigSchema
    | battery_section.BatterySectionConfigSchema
    | grid.GridConfigSchema
    | load.LoadConfigSchema
    | solar.SolarConfigSchema
    | node.NodeConfigSchema
    | connection.ConnectionConfigSchema
)

ElementConfigData = (
    inverter.InverterConfigData
    | battery.BatteryConfigData
    | battery_section.BatterySectionConfigData
    | grid.GridConfigData
    | load.LoadConfigData
    | solar.SolarConfigData
    | node.NodeConfigData
    | connection.ConnectionConfigData
)


type ElementOutputName = (
    inverter.InverterOutputName
    | battery.BatteryOutputName
    | battery_section.BatterySectionOutputName
    | connection.ConnectionOutputName
    | grid.GridOutputName
    | load.LoadOutputName
    | node.NodeOutputName
    | solar.SolarOutputName
    | NetworkOutputName
)

ELEMENT_OUTPUT_NAMES: Final[frozenset[ElementOutputName]] = frozenset(
    inverter.INVERTER_OUTPUT_NAMES
    | battery.BATTERY_OUTPUT_NAMES
    | battery_section.BATTERY_SECTION_OUTPUT_NAMES
    | connection.CONNECTION_OUTPUT_NAMES
    | grid.GRID_OUTPUT_NAMES
    | load.LOAD_OUTPUT_NAMES
    | node.NODE_OUTPUT_NAMES
    | solar.SOLAR_OUTPUT_NAMES
    | NETWORK_OUTPUT_NAMES
)

# Device translation keys for devices
# These are the translation keys used for devices created by adapters
type ElementDeviceName = (
    inverter.InverterDeviceName
    | battery.BatteryDeviceName
    | battery_section.BatterySectionDeviceName
    | connection.ConnectionDeviceName
    | grid.GridDeviceName
    | load.LoadDeviceName
    | node.NodeDeviceName
    | solar.SolarDeviceName
    | NetworkDeviceName
)

NETWORK_DEVICE_NAMES: Final[frozenset[NetworkDeviceName]] = frozenset(("network",))

ELEMENT_DEVICE_NAMES: Final[frozenset[ElementDeviceName]] = frozenset(
    inverter.INVERTER_DEVICE_NAMES
    | battery.BATTERY_DEVICE_NAMES
    | battery_section.BATTERY_SECTION_DEVICE_NAMES
    | connection.CONNECTION_DEVICE_NAMES
    | grid.GRID_DEVICE_NAMES
    | load.LOAD_DEVICE_NAMES
    | node.NODE_DEVICE_NAMES
    | solar.SOLAR_DEVICE_NAMES
    | NETWORK_DEVICE_NAMES
)

ELEMENT_DEVICE_NAMES_BY_TYPE: Final[dict[str, frozenset[ElementDeviceName]]] = {
    inverter.ELEMENT_TYPE: frozenset(inverter.INVERTER_DEVICE_NAMES),
    battery.ELEMENT_TYPE: frozenset(battery.BATTERY_DEVICE_NAMES),
    battery_section.ELEMENT_TYPE: frozenset(battery_section.BATTERY_SECTION_DEVICE_NAMES),
    connection.ELEMENT_TYPE: frozenset(connection.CONNECTION_DEVICE_NAMES),
    grid.ELEMENT_TYPE: frozenset(grid.GRID_DEVICE_NAMES),
    load.ELEMENT_TYPE: frozenset(load.LOAD_DEVICE_NAMES),
    node.ELEMENT_TYPE: frozenset(node.NODE_DEVICE_NAMES),
    solar.ELEMENT_TYPE: frozenset(solar.SOLAR_DEVICE_NAMES),
    ELEMENT_TYPE_NETWORK: frozenset(NETWORK_DEVICE_NAMES),
}


@runtime_checkable
class ElementAdapter(Protocol):
    """Protocol for element adapters.

    Each element type provides an adapter that bridges Home Assistant
    configuration with the LP model layer. Adapters must implement this
    protocol and be registered in the ELEMENT_TYPES registry.

    Note: Attributes are defined as read-only properties in the Protocol,
    but implementations use class attributes with Final for immutability.
    """

    element_type: str
    """The element type identifier."""

    advanced: bool
    """Whether this element type requires advanced mode."""

    connectivity: ConnectivityLevel
    """Visibility level in connection selectors."""

    def available(self, config: Any, *, hass: HomeAssistant, **kwargs: Any) -> bool:
        """Check if element configuration can be loaded."""
        ...

    def inputs(self, config: Mapping[str, Any] | None) -> InputFieldGroups:
        """Return input field definitions for this element."""
        ...

    def model_elements(self, config: Any) -> list[ModelElementConfig]:
        """Return model element parameters for the loaded config."""
        ...

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[Any, Mapping[Any, OutputData]]:
        """Map model outputs to device-specific outputs."""
        ...


ELEMENT_TYPES: dict[ElementType, ElementAdapter] = {
    grid.ELEMENT_TYPE: grid.adapter,
    load.ELEMENT_TYPE: load.adapter,
    inverter.ELEMENT_TYPE: inverter.adapter,
    solar.ELEMENT_TYPE: solar.adapter,
    battery.ELEMENT_TYPE: battery.adapter,
    connection.ELEMENT_TYPE: connection.adapter,
    node.ELEMENT_TYPE: node.adapter,
    battery_section.ELEMENT_TYPE: battery_section.adapter,
}


def get_element_flow_classes() -> dict[ElementType, type]:
    """Return mapping of element types to their config flow handler classes.

    This function performs lazy imports to avoid circular dependencies
    (flows import adapters, not the other way around).
    """
    # Local imports to avoid circular dependencies with flow modules
    from custom_components.haeo.elements.battery.flow import BatterySubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.elements.battery_section.flow import BatterySectionSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.elements.connection.flow import ConnectionSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.elements.grid.flow import GridSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.elements.inverter.flow import InverterSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.elements.load.flow import LoadSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.elements.node.flow import NodeSubentryFlowHandler  # noqa: PLC0415
    from custom_components.haeo.elements.solar.flow import SolarSubentryFlowHandler  # noqa: PLC0415

    return {
        "battery": BatterySubentryFlowHandler,
        "battery_section": BatterySectionSubentryFlowHandler,
        "connection": ConnectionSubentryFlowHandler,
        "grid": GridSubentryFlowHandler,
        "inverter": InverterSubentryFlowHandler,
        "load": LoadSubentryFlowHandler,
        "node": NodeSubentryFlowHandler,
        "solar": SolarSubentryFlowHandler,
    }


class ValidatedElementSubentry(NamedTuple):
    """Validated element subentry with structured configuration."""

    name: str
    element_type: ElementType
    subentry: ConfigSubentry
    config: ElementConfigSchema


# Map element types to their ConfigSchema TypedDict classes for reflection
# Typed with ElementType keys to enable type-safe indexing after is_element_type check
ELEMENT_CONFIG_SCHEMAS: Final[dict[ElementType, type]] = {
    "battery": battery.BatteryConfigSchema,
    "battery_section": battery_section.BatterySectionConfigSchema,
    "connection": connection.ConnectionConfigSchema,
    "grid": grid.GridConfigSchema,
    "inverter": inverter.InverterConfigSchema,
    "load": load.LoadConfigSchema,
    "node": node.NodeConfigSchema,
    "solar": solar.SolarConfigSchema,
}

# Map element types to their ConfigData TypedDict classes for reflection
ELEMENT_CONFIG_DATA: Final[dict[ElementType, type]] = {
    "battery": battery.BatteryConfigData,
    "battery_section": battery_section.BatterySectionConfigData,
    "connection": connection.ConnectionConfigData,
    "grid": grid.GridConfigData,
    "inverter": inverter.InverterConfigData,
    "load": load.LoadConfigData,
    "node": node.NodeConfigData,
    "solar": solar.SolarConfigData,
}

# Optional input fields per element type (used for required field checks)
ELEMENT_OPTIONAL_INPUT_FIELDS: Final[dict[ElementType, frozenset[str]]] = {
    "battery": battery.OPTIONAL_INPUT_FIELDS,
    "battery_section": battery_section.OPTIONAL_INPUT_FIELDS,
    "connection": connection.OPTIONAL_INPUT_FIELDS,
    "grid": grid.OPTIONAL_INPUT_FIELDS,
    "inverter": inverter.OPTIONAL_INPUT_FIELDS,
    "load": load.OPTIONAL_INPUT_FIELDS,
    "node": node.OPTIONAL_INPUT_FIELDS,
    "solar": solar.OPTIONAL_INPUT_FIELDS,
}


def get_input_field_schema_info(
    element_type: ElementType,
    input_fields: InputFieldGroups,
) -> dict[str, dict[str, FieldSchemaInfo]]:
    """Return schema metadata for input fields grouped by section."""
    schema_cls = ELEMENT_CONFIG_SCHEMAS[element_type]
    schema_hints = get_type_hints(schema_cls)
    schema_optional_keys: frozenset[str] = getattr(schema_cls, "__optional_keys__", frozenset())

    results: dict[str, dict[str, FieldSchemaInfo]] = {}

    for section_key, section_fields in input_fields.items():
        section_hint = schema_hints.get(section_key)
        if section_hint is None:
            msg = f"Section '{section_key}' not found in {schema_cls.__name__}"
            raise RuntimeError(msg)

        section_type = _unwrap_required_type(section_hint)
        if isinstance(section_type, TypeAliasType):
            section_type = section_type.__value__

        if not isinstance(section_type, type) or not hasattr(section_type, "__required_keys__"):
            msg = f"Section '{section_key}' in {schema_cls.__name__} is not a TypedDict"
            raise RuntimeError(msg)

        section_optional_keys: frozenset[str] = getattr(section_type, "__optional_keys__", frozenset())
        section_is_optional = section_key in schema_optional_keys
        section_hints = get_type_hints(section_type)

        section_info: dict[str, FieldSchemaInfo] = {}
        for field_name in section_fields:
            field_type = section_hints.get(field_name)
            if field_type is None:
                msg = f"Field '{section_key}.{field_name}' not found in {section_type.__name__}"
                raise RuntimeError(msg)
            is_optional = section_is_optional or field_name in section_optional_keys
            section_info[field_name] = FieldSchemaInfo(value_type=field_type, is_optional=is_optional)

        results[section_key] = section_info

    return results


def is_element_type(value: Any) -> TypeGuard[ElementType]:
    """Return True when value is a valid ElementType literal.

    Use this to narrow Any values (e.g., from dict.get()) to ElementType,
    enabling type-safe access to ELEMENT_TYPES and ELEMENT_CONFIG_SCHEMAS.
    """
    return value in ELEMENT_TYPES


def _unwrap_required_type(expected_type: Any) -> Any:
    """Return the underlying type for Required/NotRequired hints."""
    origin = get_origin(expected_type)
    if origin in (NotRequired, Required):
        return get_args(expected_type)[0]
    return expected_type


def _conforms_to_typed_dict(
    value: Mapping[str, Any],
    typed_dict_cls: type,
    *,
    check_optional: bool = False,
) -> bool:
    """Check if a mapping conforms to a TypedDict's required fields and types.

    Uses reflection to get required keys and type hints from the TypedDict class.
    Only checks required fields unless check_optional is True.
    """
    # Get required keys from TypedDict
    required_keys: frozenset[str] = getattr(typed_dict_cls, "__required_keys__", frozenset())
    optional_keys: frozenset[str] = getattr(typed_dict_cls, "__optional_keys__", frozenset())

    # Get type hints for the TypedDict
    hints = get_type_hints(typed_dict_cls)

    def _matches_type(value_item: Any, expected_type: Any) -> bool:
        expected_type = _unwrap_required_type(expected_type)
        if isinstance(expected_type, TypeAliasType):
            expected_type = expected_type.__value__

        origin = get_origin(expected_type)

        # Handle Literal types by checking if value is one of the allowed values
        # For Literal, we don't do isinstance check - just ensure the field exists
        if origin is Literal:
            return True

        if origin in (types.UnionType, Union):
            union_args = get_args(expected_type)
            return any(_matches_type(value_item, arg) for arg in union_args)

        if expected_type is float and isinstance(value_item, int):
            return True

        if isinstance(expected_type, type) and hasattr(expected_type, "__required_keys__"):
            return isinstance(value_item, Mapping) and _conforms_to_typed_dict(
                value_item,
                expected_type,
                check_optional=True,
            )

        # Get the origin type for generic types (e.g., list[str] -> list)
        check_type = origin if origin is not None else expected_type
        return isinstance(value_item, check_type)

    for key in required_keys:
        if key not in value:
            return False

        # Required keys in a TypedDict always have type hints
        expected_type = hints[key]
        if not _matches_type(value[key], expected_type):
            return False

    if check_optional:
        for key in optional_keys:
            if key not in value:
                continue
            expected_type = hints.get(key)
            if expected_type is None:
                continue
            if not _matches_type(value[key], expected_type):
                return False

    return True


def is_element_config_schema(value: Any) -> TypeGuard[ElementConfigSchema]:
    """Return True when value matches any ElementConfigSchema TypedDict.

    Performs structural validation using reflection - checks that:
    - value is a mapping
    - has a valid element_type field
    - has all required fields for that element type (from TypedDict __required_keys__)
    - all required fields have the correct type (from TypedDict type hints)
    """
    if not isinstance(value, Mapping):
        return False

    element_type = value.get(CONF_ELEMENT_TYPE)
    if not is_element_type(element_type):
        return False

    # Get the TypedDict class - type-safe because is_element_type narrowed element_type
    schema_cls = ELEMENT_CONFIG_SCHEMAS[element_type]

    return _conforms_to_typed_dict(value, schema_cls)


def is_element_config_data(value: Any) -> TypeGuard[ElementConfigData]:
    """Return True when value matches any ElementConfigData TypedDict.

    Checks required keys and types, plus optional key types when present.
    """
    if not isinstance(value, Mapping):
        return False

    element_type = value.get(CONF_ELEMENT_TYPE)
    if not is_element_type(element_type):
        return False

    data_cls = ELEMENT_CONFIG_DATA[element_type]
    return _conforms_to_typed_dict(value, data_cls, check_optional=True)


def collect_element_subentries(entry: ConfigEntry) -> list[ValidatedElementSubentry]:
    """Return validated element subentries excluding the network element."""
    result: list[ValidatedElementSubentry] = []

    for subentry in entry.subentries.values():
        if subentry.subentry_type not in ELEMENT_TYPES:
            # Not an element type (e.g., network) - skip silently
            continue

        if not is_element_config_schema(subentry.data):
            # Element type but failed validation - log warning
            _LOGGER.warning(
                "Subentry '%s' (type=%s) failed config validation and will be excluded. Data: %s",
                subentry.title,
                subentry.subentry_type,
                dict(subentry.data),
            )
            continue

        result.append(
            ValidatedElementSubentry(
                name=subentry.title,
                element_type=subentry.data[CONF_ELEMENT_TYPE],
                subentry=subentry,
                config=subentry.data,
            )
        )

    return result


def get_input_fields(element_config: ElementConfigSchema) -> InputFieldGroups:
    """Return input field definitions for an element config."""
    element_type = element_config[CONF_ELEMENT_TYPE]
    adapter = ELEMENT_TYPES[element_type]
    return adapter.inputs(element_config)


def iter_input_field_paths(input_fields: InputFieldGroups) -> list[tuple[InputFieldPath, InputFieldInfo[Any]]]:
    """Return (field_path, InputFieldInfo) pairs from nested input fields."""
    results: list[tuple[InputFieldPath, InputFieldInfo[Any]]] = []
    for section_key, section_fields in input_fields.items():
        for field_name, field_info in section_fields.items():
            results.append(((section_key, field_name), field_info))
    return results


def get_nested_config_value(config: Mapping[str, Any], field_name: str) -> Any | None:
    """Find a field value in a nested element config."""
    for value in config.values():
        if isinstance(value, Mapping):
            if field_name in value:
                return value[field_name]
            nested_value = get_nested_config_value(value, field_name)
            if nested_value is not None:
                return nested_value
    return None


def find_nested_config_path(config: Mapping[str, Any], field_name: str) -> InputFieldPath | None:
    """Find the path to a field in a nested element config."""
    for key, value in config.items():
        if key == field_name:
            return (key,)
        if isinstance(value, Mapping):
            nested = find_nested_config_path(value, field_name)
            if nested is not None:
                return (key, *nested)
    return None


def get_nested_config_value_by_path(config: Mapping[str, Any], field_path: InputFieldPath) -> Any | None:
    """Find a field value in a nested element config using a path."""
    current: Any = config
    for key in field_path:
        if not isinstance(current, Mapping):
            return None
        if key not in current:
            return None
        current = current[key]
    return current


def set_nested_config_value(config: dict[str, Any], field_name: str, value: Any) -> bool:
    """Set a field value in a nested element config."""
    for nested in config.values():
        if isinstance(nested, dict):
            if field_name in nested:
                nested[field_name] = value
                return True
            if set_nested_config_value(nested, field_name, value):
                return True
    return False


def set_nested_config_value_by_path(config: dict[str, Any], field_path: InputFieldPath, value: Any) -> bool:
    """Set a field value in a nested element config using a path."""
    current: Any = config
    for key in field_path[:-1]:
        if not isinstance(current, dict):
            return False
        next_value = current.get(key)
        if not isinstance(next_value, dict):
            return False
        current = next_value
    if not isinstance(current, dict):
        return False
    current[field_path[-1]] = value
    return True


__all__ = [
    "ELEMENT_CONFIG_SCHEMAS",
    "ELEMENT_DEVICE_NAMES",
    "ELEMENT_DEVICE_NAMES_BY_TYPE",
    "ELEMENT_OPTIONAL_INPUT_FIELDS",
    "ELEMENT_TYPES",
    "ELEMENT_TYPE_BATTERY",
    "ELEMENT_TYPE_BATTERY_SECTION",
    "ELEMENT_TYPE_CONNECTION",
    "ELEMENT_TYPE_GRID",
    "ELEMENT_TYPE_INVERTER",
    "ELEMENT_TYPE_LOAD",
    "ELEMENT_TYPE_NODE",
    "ELEMENT_TYPE_SOLAR",
    "ConnectivityLevel",
    "ElementAdapter",
    "ElementConfigData",
    "ElementConfigSchema",
    "ElementDeviceName",
    "ElementType",
    "FieldSchemaInfo",
    "InputFieldGroups",
    "InputFieldInfo",
    "InputFieldPath",
    "InputFieldSection",
    "ValidatedElementSubentry",
    "collect_element_subentries",
    "find_nested_config_path",
    "get_element_flow_classes",
    "get_input_field_schema_info",
    "get_input_fields",
    "get_nested_config_value",
    "get_nested_config_value_by_path",
    "is_element_config_data",
    "is_element_config_schema",
    "is_element_type",
    "iter_input_field_paths",
    "set_nested_config_value",
    "set_nested_config_value_by_path",
]
