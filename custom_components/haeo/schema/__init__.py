"""Schema utilities for HAEO type configurations."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, Union, Unpack, cast, get_args, get_origin, get_type_hints
from typing import get_origin as typing_get_origin

import voluptuous as vol

from .fields import Constant, Default, LoaderMeta, TimeSeries, Validator
from .params import SchemaParams

if TYPE_CHECKING:
    from custom_components.haeo.data.loader import Loader

__all__ = [
    "Default",
    "FieldSpec",
    "compose_field",
    "get_default",
    "get_loader_instance",
    "get_schema_defaults",
    "schema_for_type",
]


@dataclass(frozen=True)
class FieldSpec:
    """Composed field specification from Annotated metadata.

    Aggregates validator, loader, and default metadata extracted from
    an Annotated type into a unified structure for schema generation
    and data loading.
    """

    validator: Validator | None
    loader: LoaderMeta | None
    default: Default | None


def compose_field(field_type: Any) -> FieldSpec:
    """Extract and compose metadata from an Annotated field type.

    Scans the metadata attached to an Annotated type and returns a FieldSpec
    containing the validator, loader, and default (if present).

    Args:
        field_type: An Annotated type with metadata markers.

    Returns:
        FieldSpec with extracted metadata components.

    """
    validator: Validator | None = None
    loader: LoaderMeta | None = None
    default: Default | None = None

    # Handle NotRequired wrapper
    origin = get_origin(field_type)
    if origin is not None and hasattr(origin, "__name__") and origin.__name__ == "NotRequired":
        field_type = get_args(field_type)[0]

    # Unwrap Optional[...] (Union[..., None])
    if get_origin(field_type) is Union:
        args = [a for a in get_args(field_type) if a is not type(None)]
        if len(args) == 1:
            field_type = args[0]
        elif len(args) > 1:
            for arg in args:
                if get_origin(arg) is Annotated:
                    field_type = arg
                    break

    # Extract metadata from Annotated type
    if get_origin(field_type) is Annotated:
        for meta in field_type.__metadata__:
            if isinstance(meta, Validator) and validator is None:
                validator = meta
            elif isinstance(meta, LoaderMeta) and loader is None:
                loader = meta
            elif isinstance(meta, Default) and default is None:
                default = meta

    return FieldSpec(validator=validator, loader=loader, default=default)


def get_default[T](field_name: str, config_class: type, fallback: T) -> T:
    """Get the default value for a field from its schema annotation.

    Extracts the Default metadata from a field's Annotated type and returns
    the default value. Returns the fallback if no default is defined.

    Args:
        field_name: Name of the field in the TypedDict.
        config_class: The TypedDict config class (Schema or Data mode).
        fallback: Value to return if no default is defined.

    Returns:
        The default value from the field's annotation, or fallback.

    """
    hints = get_type_hints(config_class, include_extras=True)
    field_type = hints.get(field_name)
    if field_type is None:
        return fallback

    spec = compose_field(field_type)
    if spec.default is not None:
        return cast("T", spec.default.value)
    return fallback


def _get_loader_from_meta(loader_meta: LoaderMeta | None) -> "Loader":
    """Create a loader instance from a loader metadata marker.

    Args:
        loader_meta: Loader metadata marker (ConstantFloat, TimeSeries, etc.)

    Returns:
        Concrete loader instance.

    """
    # Import locally to avoid circular import
    from custom_components.haeo.data.loader import ConstantLoader, TimeSeriesLoader  # noqa: PLC0415

    match loader_meta:
        case Constant(value_type=value_type):
            return ConstantLoader[Any](value_type)
        case TimeSeries():
            return TimeSeriesLoader()
        case None | _:
            return ConstantLoader[Any](object)


def get_loader_instance(field_name: str, config_class: type) -> "Loader":
    """Extract the loader instance from a field's annotation.

    Args:
        field_name: Name of the field
        config_class: TypedDict config class (Data mode)

    Returns:
        The loader instance

    """
    # Import locally to avoid circular import
    from custom_components.haeo.data.loader import ConstantLoader  # noqa: PLC0415

    hints = get_type_hints(config_class, include_extras=True)
    field_type = hints.get(field_name)
    if field_type is None:
        return ConstantLoader[Any](object)

    spec = compose_field(field_type)
    return _get_loader_from_meta(spec.loader)


def _get_annotated_fields(cls: type) -> dict[str, tuple[Validator, bool]]:
    """Get the annotated fields with validators for a TypedDict type.

    Returns:
        dict[field_name, (validator, is_optional)]
        where is_optional indicates if the field has NotRequired

    """
    hints = get_type_hints(cls, include_extras=True)
    annotated: dict[str, tuple[Validator, bool]] = {}

    # Get optional status from TypedDict
    optional_keys: set[str] = getattr(cls, "__optional_keys__", set())

    for field_name, field_tp in hints.items():
        # Skip element_type field
        if field_name == "element_type":
            continue

        is_optional = field_name in optional_keys

        # Handle NotRequired wrapper
        unwrapped_tp = field_tp
        origin = typing_get_origin(unwrapped_tp)
        if origin is not None and origin.__name__ == "NotRequired":
            unwrapped_tp = get_args(unwrapped_tp)[0]
            is_optional = True

        # Handle Union[..., None] (Optional) - check before compose_field
        if get_origin(unwrapped_tp) is Union:
            args = get_args(unwrapped_tp)
            if type(None) in args:
                is_optional = True

        # Compose field and extract validator
        spec = compose_field(unwrapped_tp)
        if spec.validator is not None:
            annotated[field_name] = (spec.validator, is_optional)

    return annotated


def get_schema_defaults(schema_class: type) -> dict[str, Any]:
    """Extract schema default values from a ConfigSchema type.

    Iterates through field annotations and extracts Default.value values
    for use as suggested values in config flow forms.

    Args:
        schema_class: TypedDict config schema class (Schema mode)

    Returns:
        Dictionary mapping field names to their schema default values.
        Only fields with Default markers are included.

    """
    defaults: dict[str, Any] = {}
    hints = get_type_hints(schema_class, include_extras=True)

    for field_name, field_type in hints.items():
        spec = compose_field(field_type)
        if spec.default is not None:
            defaults[field_name] = spec.default.value

    return defaults


def schema_for_type(cls: type, **schema_params: Unpack[SchemaParams]) -> vol.Schema:
    """Create a schema for a TypedDict type.

    Args:
        cls: The TypedDict class to create schema for
        **schema_params: Schema parameters passed to field validators

    Returns:
        Voluptuous schema

    """
    annotated_fields = _get_annotated_fields(cls)
    schema: dict[vol.Required | vol.Optional, vol.All] = {}
    for field, (validator, is_optional) in annotated_fields.items():
        vol_schema = validator.create_schema(**schema_params)
        schema_key = (vol.Optional if is_optional else vol.Required)(field)
        schema[schema_key] = vol_schema

    return vol.Schema(schema)
