"""Structural check that a mapping is an element config schema."""

from collections.abc import Mapping, Sequence
import types
from typing import (
    Any,  # noqa: TID251  # reflection over typing constructs (get_origin/get_args on type hints)
    Literal,
    TypeAliasType,
    TypeGuard,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements import ELEMENT_CONFIG_SCHEMAS, ElementConfigSchema


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
            if not _matches_type(value[key], hints[key]):
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
    schema_cls = next((cls for kind, cls in ELEMENT_CONFIG_SCHEMAS.items() if kind == element_type), None)
    return schema_cls is not None and _conforms_to_typed_dict(value, schema_cls)


__all__ = ["is_element_config_schema"]
