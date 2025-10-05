"""Schema utilities for flattening and reconstructing HAEO type configurations."""

from dataclasses import MISSING
from dataclasses import fields as dataclass_fields
from typing import Annotated, Any, TypeVar, Union, get_args, get_origin, get_type_hints

import voluptuous as vol

from .fields import FieldMeta

T = TypeVar("T")


def _get_annotated_fields(cls: type) -> dict[str, tuple[FieldMeta, bool, object]]:
    """Get the annotated fields for a dataclass type.

    Returns:
        dict[field_name, (metadata_list, is_optional, default_value)]
        where default_value is:
            - the actual default, if one exists (even None)
            - MISSING if no default was provided

    """
    hints = get_type_hints(cls, include_extras=True)
    annotated: dict[str, tuple[FieldMeta, bool, object]] = {}
    for f in dataclass_fields(cls):
        tp = hints[f.name]
        is_optional = False

        # Unwrap Optional[...] (Union[..., None])
        if get_origin(tp) is Union:
            args = [a for a in get_args(tp) if a is not type(None)]
            if len(args) == 1:
                tp = args[0]
                is_optional = True

        # Extract Annotated metadata
        if get_origin(tp) is Annotated:
            *_, meta = get_args(tp)

            annotated[f.name] = (meta, is_optional, f.default)

    return annotated


def schema_for_type(cls: type, **kwargs: Any) -> vol.Schema:
    """Create a schema for a type."""
    annotated_fields = _get_annotated_fields(cls)

    schema = {}
    for field, (meta, optional, default) in annotated_fields.items():
        for k, s in meta.create_schema(**kwargs).items():
            key = f"{field}_{k}"
            schema_key = (vol.Optional if optional else vol.Required)(
                key, default=default if default not in (MISSING, None) else vol.UNDEFINED
            )
            schema[schema_key] = s

    return vol.Schema(schema)


def data_to_config[T](cls: type[T], data: dict[str, Any]) -> T:
    """Convert data to a configuration class."""
    annotated_fields = _get_annotated_fields(cls)
    output: dict[str, Any] = {}

    for field, (meta, is_optional, default) in annotated_fields.items():
        field_data = {}
        schema_keys = list(meta.create_schema().keys())

        # Collect all data for this field using .get() to handle missing keys
        for k in schema_keys:
            key = f"{field}_{k}"
            field_data[k] = data.get(key)

        # Handle missing optional fields - use default if provided
        if not any(field_data.values()) and is_optional:
            if default is not None and default is not MISSING:
                if callable(default):
                    output[field] = default()
                else:
                    output[field] = default
            else:
                output[field] = None  # Default for optional fields when not provided
            continue

        # Handle missing required fields - use default if provided
        if not any(field_data.values()) and not is_optional:
            if default is not None and default is not MISSING:
                if callable(default):
                    output[field] = default()
                else:
                    output[field] = default
                continue
            # This shouldn't happen if schema validation passed
            msg = f"Missing required field: {field!r}"
            raise ValueError(msg)

        # Convert field data to appropriate format based on field type
        field_type = meta.field_type[1]  # "constant", "sensor", "forecast", etc.

        if field_type == "constant":
            # For constant fields, extract the single value if present
            value = field_data.get("value")
            output[field] = value if value is not None else field_data
        else:
            # For non-constant fields, keep the structure as-is
            output[field] = field_data

    return cls(**output)
