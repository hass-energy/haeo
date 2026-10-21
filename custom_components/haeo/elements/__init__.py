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

from collections.abc import Mapping, MutableSequence, Sequence
import logging
import types
from typing import (
    Any,  # noqa: TID251  # reflection over typing constructs (get_origin/get_args on type hints)
    Final,
    Literal,
    NamedTuple,
    TypeAliasType,
    TypeGuard,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from homeassistant.config_entries import ConfigEntry, ConfigSubentry

from custom_components.haeo.const import (
    ELEMENT_TYPE_NETWORK,
    NETWORK_DEVICE_NAMES,
    NETWORK_OUTPUT_NAMES,
    NetworkDeviceName,
    NetworkOutputName,
)
from custom_components.haeo.core.adapters.elements.battery import (
    BATTERY_DEVICE_NAMES,
    BATTERY_OUTPUT_NAMES,
    BatteryDeviceName,
    BatteryOutputName,
)
from custom_components.haeo.core.adapters.elements.battery_section import (
    BATTERY_SECTION_DEVICE_NAMES,
    BATTERY_SECTION_OUTPUT_NAMES,
    BatterySectionDeviceName,
    BatterySectionOutputName,
)
from custom_components.haeo.core.adapters.elements.buffer import (
    BUFFER_DEVICE_NAMES,
    BUFFER_OUTPUT_NAMES,
    BufferDeviceName,
    BufferOutputName,
)
from custom_components.haeo.core.adapters.elements.connection import (
    CONNECTION_DEVICE_NAMES,
    CONNECTION_OUTPUT_NAMES,
    ConnectionDeviceName,
    ConnectionOutputName,
)
from custom_components.haeo.core.adapters.elements.deferrable_load import (
    DEFERRABLE_LOAD_DEVICE_NAMES,
    DEFERRABLE_LOAD_ELEMENT_OUTPUT_NAMES,
    DeferrableLoadDeviceName,
    DeferrableLoadElementOutputName,
)
from custom_components.haeo.core.adapters.elements.ev import (
    EV_DEVICE_NAMES,
    EV_OUTPUT_NAMES,
    EvDeviceName,
    EvOutputName,
)
from custom_components.haeo.core.adapters.elements.grid import (
    GRID_DEVICE_NAMES,
    GRID_OUTPUT_NAMES,
    GridDeviceName,
    GridOutputName,
)
from custom_components.haeo.core.adapters.elements.inverter import (
    INVERTER_DEVICE_NAMES,
    INVERTER_OUTPUT_NAMES,
    InverterDeviceName,
    InverterOutputName,
)
from custom_components.haeo.core.adapters.elements.junction import (
    JUNCTION_DEVICE_NAMES,
    JUNCTION_OUTPUT_NAMES,
    JunctionDeviceName,
    JunctionOutputName,
)
from custom_components.haeo.core.adapters.elements.load import (
    LOAD_DEVICE_NAMES,
    LOAD_OUTPUT_NAMES,
    LoadDeviceName,
    LoadOutputName,
)
from custom_components.haeo.core.adapters.elements.node import (
    NODE_DEVICE_NAMES,
    NODE_OUTPUT_NAMES,
    NodeDeviceName,
    NodeOutputName,
)
from custom_components.haeo.core.adapters.elements.policy import POLICY_DEVICE_NAMES, PolicyDeviceName
from custom_components.haeo.core.adapters.elements.solar import (
    SOLAR_DEVICE_NAMES,
    SOLAR_OUTPUT_NAMES,
    SolarDeviceName,
    SolarOutputName,
)
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES, is_element_type
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements import ELEMENT_CONFIG_SCHEMAS, ElementConfigSchema, ElementType
from custom_components.haeo.core.schema.field_hints import extract_field_hints, extract_list_field_hints
from custom_components.haeo.core.schema.field_schema import FieldSchemaInfo
from custom_components.haeo.core.schema.surfaced_policy import get_surfaced_price_hints
from custom_components.haeo.elements.field_hints import build_input_fields, build_list_input_fields

from .input_fields import AnyInputFieldInfo, InputFieldGroups, InputFieldInfo, InputFieldPath, InputFieldSection

_LOGGER = logging.getLogger(__name__)


type ElementOutputName = (
    InverterOutputName
    | BatteryOutputName
    | BatterySectionOutputName
    | ConnectionOutputName
    | DeferrableLoadElementOutputName
    | EvOutputName
    | GridOutputName
    | LoadOutputName
    | NodeOutputName
    | JunctionOutputName
    | SolarOutputName
    | BufferOutputName
    | NetworkOutputName
)

ELEMENT_OUTPUT_NAMES: Final[frozenset[ElementOutputName]] = frozenset(
    INVERTER_OUTPUT_NAMES
    | BATTERY_OUTPUT_NAMES
    | BATTERY_SECTION_OUTPUT_NAMES
    | CONNECTION_OUTPUT_NAMES
    | DEFERRABLE_LOAD_ELEMENT_OUTPUT_NAMES
    | EV_OUTPUT_NAMES
    | GRID_OUTPUT_NAMES
    | LOAD_OUTPUT_NAMES
    | NODE_OUTPUT_NAMES
    | JUNCTION_OUTPUT_NAMES
    | SOLAR_OUTPUT_NAMES
    | BUFFER_OUTPUT_NAMES
    | NETWORK_OUTPUT_NAMES
)

type ElementDeviceName = (
    InverterDeviceName
    | BatteryDeviceName
    | BatterySectionDeviceName
    | ConnectionDeviceName
    | DeferrableLoadDeviceName
    | EvDeviceName
    | GridDeviceName
    | LoadDeviceName
    | NodeDeviceName
    | JunctionDeviceName
    | SolarDeviceName
    | PolicyDeviceName
    | BufferDeviceName
    | NetworkDeviceName
)


ELEMENT_DEVICE_NAMES: Final[frozenset[ElementDeviceName]] = frozenset(
    INVERTER_DEVICE_NAMES
    | BATTERY_DEVICE_NAMES
    | BATTERY_SECTION_DEVICE_NAMES
    | CONNECTION_DEVICE_NAMES
    | DEFERRABLE_LOAD_DEVICE_NAMES
    | EV_DEVICE_NAMES
    | GRID_DEVICE_NAMES
    | LOAD_DEVICE_NAMES
    | NODE_DEVICE_NAMES
    | JUNCTION_DEVICE_NAMES
    | SOLAR_DEVICE_NAMES
    | POLICY_DEVICE_NAMES
    | BUFFER_DEVICE_NAMES
    | NETWORK_DEVICE_NAMES
)

ELEMENT_DEVICE_NAMES_BY_TYPE: Final[Mapping[str, frozenset[str]]] = {
    **{element_type: adapter.device_names for element_type, adapter in ELEMENT_TYPES.items()},
    ELEMENT_TYPE_NETWORK: NETWORK_DEVICE_NAMES,
}


class ValidatedElementSubentry(NamedTuple):
    """Validated element subentry with structured configuration."""

    name: str
    element_type: ElementType
    subentry: ConfigSubentry
    config: ElementConfigSchema


def get_input_field_schema_info(
    element_type: ElementType,
    input_fields: InputFieldGroups,
) -> dict[str, dict[str, FieldSchemaInfo]]:
    """Return schema metadata for input fields grouped by section."""
    schema_cls = ELEMENT_CONFIG_SCHEMAS[element_type]
    schema_hints = get_type_hints(schema_cls)

    results: dict[str, dict[str, FieldSchemaInfo]] = {}

    for section_key, section_fields in input_fields.items():
        section_hint = schema_hints.get(section_key)
        if section_hint is None:
            msg = f"Section '{section_key}' not found in {schema_cls.__name__}"
            raise RuntimeError(msg)

        section_type = section_hint
        if isinstance(section_type, TypeAliasType):
            section_type = section_type.__value__

        if not isinstance(section_type, type) or not hasattr(section_type, "__required_keys__"):
            msg = f"Section '{section_key}' in {schema_cls.__name__} is not a TypedDict"
            raise RuntimeError(msg)

        section_optional_keys: frozenset[str] = getattr(section_type, "__optional_keys__", frozenset())
        section_hints = get_type_hints(section_type)

        section_info: dict[str, FieldSchemaInfo] = {}
        for field_name in section_fields:
            field_type = section_hints.get(field_name)
            if field_type is None:
                msg = f"Field '{section_key}.{field_name}' not found in {section_type.__name__}"
                raise RuntimeError(msg)
            section_info[field_name] = FieldSchemaInfo(
                value_type=field_type, is_optional=field_name in section_optional_keys
            )

        results[section_key] = section_info

    return results


def _conforms_to_typed_dict(
    value: Mapping[str, object],
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

    def _matches_type(value_item: object, expected_type: Any) -> bool:
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
        # HA's deep-freeze converts list→tuple, so accept any sequence where list is expected
        check_type = origin if origin is not None else expected_type
        if check_type is list:
            return isinstance(value_item, Sequence) and not isinstance(value_item, str)
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


def is_element_config_schema(value: object) -> TypeGuard[ElementConfigSchema]:
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


def get_element_configs(
    entry: ConfigEntry,
    participant_subentry_ids: Mapping[str, str],
) -> dict[str, ElementConfigSchema]:
    """Read fresh, typed element configs from a config entry's subentries.

    This is the typed boundary between Home Assistant's untyped
    ``MappingProxyType[str, Any]`` subentry data and HAEO's
    ``ElementConfigSchema`` TypedDicts.  Each subentry is validated via the
    ``is_element_config_schema`` TypeGuard so downstream code receives fully
    narrowed types with no ``Any``.

    Raises ValueError if any subentry fails validation — these were already
    validated at init by ``collect_element_subentries``, so a failure here
    indicates a bug.
    """
    subentries = entry.subentries
    configs: dict[str, ElementConfigSchema] = {}
    for name, subentry_id in participant_subentry_ids.items():
        if subentry_id not in subentries:
            continue
        data = subentries[subentry_id].data
        if not is_element_config_schema(data):
            msg = f"Subentry '{name}' failed config validation on read"
            raise ValueError(msg)
        configs[name] = data
    return configs


def get_input_fields(element_type: ElementType) -> InputFieldGroups:
    """Return input field definitions for an element type."""
    return build_input_fields(str(element_type), extract_field_hints(ELEMENT_CONFIG_SCHEMAS[element_type]))


def get_list_input_fields(element_config: Mapping[str, object]) -> InputFieldGroups:
    """Return dynamic input fields for list-based config structures.

    Finds list fields annotated with ``ListFieldHints`` and generates
    per-item input field definitions based on the actual config data.
    Field paths use ``(list_key, str(index), field_name)`` to navigate
    into the list items.
    """
    element_type = element_config.get(CONF_ELEMENT_TYPE)
    if not is_element_type(element_type):
        return {}

    schema_cls = ELEMENT_CONFIG_SCHEMAS.get(element_type)
    if schema_cls is None:
        return {}

    list_hints = extract_list_field_hints(schema_cls)
    if not list_hints:
        return {}

    result: dict[str, dict[str, AnyInputFieldInfo]] = {}
    for list_key, hints in list_hints.items():
        items = element_config.get(list_key)
        if not isinstance(items, Sequence) or isinstance(items, str):
            continue
        result.update(
            build_list_input_fields(str(element_type), list_key, hints, items),
        )

    return result


def get_surfaced_input_fields(element_type: str | ElementType) -> dict[str, AnyInputFieldInfo]:
    """Return InputFieldInfo objects for surfaced pricing fields.

    These fields appear on the element's config flow but are stored as
    policy rules. The InputFieldInfo objects drive selector construction
    and form defaults through the standard field system.
    """
    hints = get_surfaced_price_hints(str(element_type))
    if not hints:
        return {}
    section_fields = build_input_fields(
        str(element_type), {"_surfaced": {name: hint.hint for name, hint in hints.items()}}
    )
    return section_fields.get("_surfaced", {})


def iter_input_field_paths(input_fields: InputFieldGroups) -> list[tuple[InputFieldPath, AnyInputFieldInfo]]:
    """Return (input_path, InputFieldInfo) pairs for every input of the nested fields.

    For section-based fields, paths are 2-tuples: ``(section_key, field_name)``.
    For list-based fields (section keys containing ``"."``), paths are expanded
    into 3-tuples: ``(list_key, index, field_name)``. A field with outputs
    yields its outputs in its place; read their config value from
    :func:`config_field_path`.
    """
    results: list[tuple[InputFieldPath, AnyInputFieldInfo]] = []
    for section_key, section_fields in input_fields.items():
        prefix = tuple(section_key.split(".")) if "." in section_key else (section_key,)
        for field_name, field_info in section_fields.items():
            if field_info.outputs:
                results.extend(((*prefix, name), output) for name, output in field_info.outputs.items())
            else:
                results.append(((*prefix, field_name), field_info))
    return results


def config_field_path(input_path: InputFieldPath, field_info: AnyInputFieldInfo) -> InputFieldPath:
    """Return the config path an input reads: its own, or that of the field feeding it."""
    if field_info.source_field is None:
        return input_path
    return (*input_path[:-1], field_info.source_field)


def get_nested_config_value(config: Mapping[str, object], field_name: str) -> object | None:
    """Find a field value in a nested element config."""
    for value in config.values():
        if isinstance(value, Mapping):
            if field_name in value:
                return value[field_name]
            nested_value = get_nested_config_value(value, field_name)
            if nested_value is not None:
                return nested_value
    return None


def find_nested_config_path(config: Mapping[str, object], field_name: str) -> InputFieldPath | None:
    """Find the path to a field in a nested element config."""
    for key, value in config.items():
        if key == field_name:
            return (key,)
        if isinstance(value, Mapping):
            nested = find_nested_config_path(value, field_name)
            if nested is not None:
                return (key, *nested)
    return None


def set_nested_config_value(config: dict[str, object], field_name: str, value: object) -> bool:
    """Set a field value in a nested element config."""
    for nested in config.values():
        if isinstance(nested, dict):
            if field_name in nested:
                nested[field_name] = value
                return True
            if set_nested_config_value(nested, field_name, value):
                return True
    return False


def set_nested_config_value_by_path(config: dict[str, object], field_path: InputFieldPath, value: object) -> bool:
    """Set a field value in a nested element config using a path.

    Supports both mapping keys and integer indices for list traversal.
    """
    current: object = config
    for key in field_path[:-1]:
        if isinstance(current, dict):
            next_value = current.get(key)
            if isinstance(next_value, (dict, Sequence)) and not isinstance(next_value, str):
                current = next_value
            else:
                return False
        elif isinstance(current, Sequence) and not isinstance(current, str):
            try:
                current = current[int(key)]
            except (ValueError, IndexError):
                return False
        else:
            return False
    last_key = field_path[-1]
    if isinstance(current, dict):
        current[last_key] = value
        return True
    if isinstance(current, MutableSequence):
        try:
            current[int(last_key)] = value
            return True
        except (ValueError, IndexError):
            return False
    return False


__all__ = [
    "ELEMENT_DEVICE_NAMES",
    "ELEMENT_DEVICE_NAMES_BY_TYPE",
    "ElementDeviceName",
    "ElementOutputName",
    "FieldSchemaInfo",
    "InputFieldGroups",
    "InputFieldInfo",
    "InputFieldPath",
    "InputFieldSection",
    "ValidatedElementSubentry",
    "collect_element_subentries",
    "config_field_path",
    "find_nested_config_path",
    "get_element_configs",
    "get_input_field_schema_info",
    "get_input_fields",
    "get_list_input_fields",
    "get_nested_config_value",
    "get_surfaced_input_fields",
    "is_element_config_schema",
    "iter_input_field_paths",
    "set_nested_config_value",
    "set_nested_config_value_by_path",
]
