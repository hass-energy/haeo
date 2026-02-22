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

from custom_components.haeo.adapters.elements.battery import (
    BATTERY_DEVICE_NAMES,
    BATTERY_OUTPUT_NAMES,
    BatteryDeviceName,
    BatteryOutputName,
)
from custom_components.haeo.adapters.elements.battery import adapter as battery_adapter
from custom_components.haeo.adapters.elements.battery_section import (
    BATTERY_SECTION_DEVICE_NAMES,
    BATTERY_SECTION_OUTPUT_NAMES,
    BatterySectionDeviceName,
    BatterySectionOutputName,
)
from custom_components.haeo.adapters.elements.battery_section import adapter as battery_section_adapter
from custom_components.haeo.adapters.elements.connection import (
    CONNECTION_DEVICE_NAMES,
    CONNECTION_OUTPUT_NAMES,
    ConnectionDeviceName,
    ConnectionOutputName,
)
from custom_components.haeo.adapters.elements.connection import adapter as connection_adapter
from custom_components.haeo.adapters.elements.grid import (
    GRID_DEVICE_NAMES,
    GRID_OUTPUT_NAMES,
    GridDeviceName,
    GridOutputName,
)
from custom_components.haeo.adapters.elements.grid import adapter as grid_adapter
from custom_components.haeo.adapters.elements.inverter import (
    INVERTER_DEVICE_NAMES,
    INVERTER_OUTPUT_NAMES,
    InverterDeviceName,
    InverterOutputName,
)
from custom_components.haeo.adapters.elements.inverter import adapter as inverter_adapter
from custom_components.haeo.adapters.elements.load import (
    LOAD_DEVICE_NAMES,
    LOAD_OUTPUT_NAMES,
    LoadDeviceName,
    LoadOutputName,
)
from custom_components.haeo.adapters.elements.load import adapter as load_adapter
from custom_components.haeo.adapters.elements.node import (
    NODE_DEVICE_NAMES,
    NODE_OUTPUT_NAMES,
    NodeDeviceName,
    NodeOutputName,
)
from custom_components.haeo.adapters.elements.node import adapter as node_adapter
from custom_components.haeo.adapters.elements.solar import (
    SOLAR_DEVICE_NAMES,
    SOLAR_OUTPUT_NAMES,
    SolarDeviceName,
    SolarOutputName,
)
from custom_components.haeo.adapters.elements.solar import adapter as solar_adapter
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
from custom_components.haeo.schema.elements.battery import OPTIONAL_INPUT_FIELDS as BATTERY_OPTIONAL_INPUT_FIELDS
from custom_components.haeo.schema.elements.battery import BatteryConfigData, BatteryConfigSchema
from custom_components.haeo.schema.elements.battery_section import (
    OPTIONAL_INPUT_FIELDS as BATTERY_SECTION_OPTIONAL_INPUT_FIELDS,
)
from custom_components.haeo.schema.elements.battery_section import BatterySectionConfigData, BatterySectionConfigSchema
from custom_components.haeo.schema.elements.connection import OPTIONAL_INPUT_FIELDS as CONNECTION_OPTIONAL_INPUT_FIELDS
from custom_components.haeo.schema.elements.connection import ConnectionConfigData, ConnectionConfigSchema
from custom_components.haeo.schema.elements.grid import OPTIONAL_INPUT_FIELDS as GRID_OPTIONAL_INPUT_FIELDS
from custom_components.haeo.schema.elements.grid import GridConfigData, GridConfigSchema
from custom_components.haeo.schema.elements.inverter import OPTIONAL_INPUT_FIELDS as INVERTER_OPTIONAL_INPUT_FIELDS
from custom_components.haeo.schema.elements.inverter import InverterConfigData, InverterConfigSchema
from custom_components.haeo.schema.elements.load import OPTIONAL_INPUT_FIELDS as LOAD_OPTIONAL_INPUT_FIELDS
from custom_components.haeo.schema.elements.load import LoadConfigData, LoadConfigSchema
from custom_components.haeo.schema.elements.node import OPTIONAL_INPUT_FIELDS as NODE_OPTIONAL_INPUT_FIELDS
from custom_components.haeo.schema.elements.node import NodeConfigData, NodeConfigSchema
from custom_components.haeo.schema.elements.solar import OPTIONAL_INPUT_FIELDS as SOLAR_OPTIONAL_INPUT_FIELDS
from custom_components.haeo.schema.elements.solar import SolarConfigData, SolarConfigSchema

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

ELEMENT_TYPE_INVERTER: Final = "inverter"
ELEMENT_TYPE_BATTERY: Final = "battery"
ELEMENT_TYPE_BATTERY_SECTION: Final = "battery_section"
ELEMENT_TYPE_CONNECTION: Final = "connection"
ELEMENT_TYPE_SOLAR: Final = "solar"
ELEMENT_TYPE_GRID: Final = "grid"
ELEMENT_TYPE_LOAD: Final = "load"
ELEMENT_TYPE_NODE: Final = "node"

ElementConfigSchema = (
    InverterConfigSchema
    | BatteryConfigSchema
    | BatterySectionConfigSchema
    | GridConfigSchema
    | LoadConfigSchema
    | SolarConfigSchema
    | NodeConfigSchema
    | ConnectionConfigSchema
)

ElementConfigData = (
    InverterConfigData
    | BatteryConfigData
    | BatterySectionConfigData
    | GridConfigData
    | LoadConfigData
    | SolarConfigData
    | NodeConfigData
    | ConnectionConfigData
)


type ElementOutputName = (
    InverterOutputName
    | BatteryOutputName
    | BatterySectionOutputName
    | ConnectionOutputName
    | GridOutputName
    | LoadOutputName
    | NodeOutputName
    | SolarOutputName
    | NetworkOutputName
)

ELEMENT_OUTPUT_NAMES: Final[frozenset[ElementOutputName]] = frozenset(
    INVERTER_OUTPUT_NAMES
    | BATTERY_OUTPUT_NAMES
    | BATTERY_SECTION_OUTPUT_NAMES
    | CONNECTION_OUTPUT_NAMES
    | GRID_OUTPUT_NAMES
    | LOAD_OUTPUT_NAMES
    | NODE_OUTPUT_NAMES
    | SOLAR_OUTPUT_NAMES
    | NETWORK_OUTPUT_NAMES
)

type ElementDeviceName = (
    InverterDeviceName
    | BatteryDeviceName
    | BatterySectionDeviceName
    | ConnectionDeviceName
    | GridDeviceName
    | LoadDeviceName
    | NodeDeviceName
    | SolarDeviceName
    | NetworkDeviceName
)

NETWORK_DEVICE_NAMES: Final[frozenset[NetworkDeviceName]] = frozenset(("network",))

ELEMENT_DEVICE_NAMES: Final[frozenset[ElementDeviceName]] = frozenset(
    INVERTER_DEVICE_NAMES
    | BATTERY_DEVICE_NAMES
    | BATTERY_SECTION_DEVICE_NAMES
    | CONNECTION_DEVICE_NAMES
    | GRID_DEVICE_NAMES
    | LOAD_DEVICE_NAMES
    | NODE_DEVICE_NAMES
    | SOLAR_DEVICE_NAMES
    | NETWORK_DEVICE_NAMES
)

ELEMENT_DEVICE_NAMES_BY_TYPE: Final[dict[str, frozenset[ElementDeviceName]]] = {
    ELEMENT_TYPE_INVERTER: frozenset(INVERTER_DEVICE_NAMES),
    ELEMENT_TYPE_BATTERY: frozenset(BATTERY_DEVICE_NAMES),
    ELEMENT_TYPE_BATTERY_SECTION: frozenset(BATTERY_SECTION_DEVICE_NAMES),
    ELEMENT_TYPE_CONNECTION: frozenset(CONNECTION_DEVICE_NAMES),
    ELEMENT_TYPE_GRID: frozenset(GRID_DEVICE_NAMES),
    ELEMENT_TYPE_LOAD: frozenset(LOAD_DEVICE_NAMES),
    ELEMENT_TYPE_NODE: frozenset(NODE_DEVICE_NAMES),
    ELEMENT_TYPE_SOLAR: frozenset(SOLAR_DEVICE_NAMES),
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
    ELEMENT_TYPE_GRID: grid_adapter,
    ELEMENT_TYPE_LOAD: load_adapter,
    ELEMENT_TYPE_INVERTER: inverter_adapter,
    ELEMENT_TYPE_SOLAR: solar_adapter,
    ELEMENT_TYPE_BATTERY: battery_adapter,
    ELEMENT_TYPE_CONNECTION: connection_adapter,
    ELEMENT_TYPE_NODE: node_adapter,
    ELEMENT_TYPE_BATTERY_SECTION: battery_section_adapter,
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
    "battery": BatteryConfigSchema,
    "battery_section": BatterySectionConfigSchema,
    "connection": ConnectionConfigSchema,
    "grid": GridConfigSchema,
    "inverter": InverterConfigSchema,
    "load": LoadConfigSchema,
    "node": NodeConfigSchema,
    "solar": SolarConfigSchema,
}

ELEMENT_CONFIG_DATA: Final[dict[ElementType, type]] = {
    "battery": BatteryConfigData,
    "battery_section": BatterySectionConfigData,
    "connection": ConnectionConfigData,
    "grid": GridConfigData,
    "inverter": InverterConfigData,
    "load": LoadConfigData,
    "node": NodeConfigData,
    "solar": SolarConfigData,
}

ELEMENT_OPTIONAL_INPUT_FIELDS: Final[dict[ElementType, frozenset[str]]] = {
    "battery": BATTERY_OPTIONAL_INPUT_FIELDS,
    "battery_section": BATTERY_SECTION_OPTIONAL_INPUT_FIELDS,
    "connection": CONNECTION_OPTIONAL_INPUT_FIELDS,
    "grid": GRID_OPTIONAL_INPUT_FIELDS,
    "inverter": INVERTER_OPTIONAL_INPUT_FIELDS,
    "load": LOAD_OPTIONAL_INPUT_FIELDS,
    "node": NODE_OPTIONAL_INPUT_FIELDS,
    "solar": SOLAR_OPTIONAL_INPUT_FIELDS,
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
