"""Schema utilities for HAEO type configurations."""

from collections.abc import Sequence
import importlib
from typing import TYPE_CHECKING, Annotated, Any, TypeVar, Union, Unpack, cast, get_args, get_origin, get_type_hints
from typing import get_origin as typing_get_origin

from homeassistant.core import HomeAssistant
import voluptuous as vol

from custom_components.haeo.data.loader import ConstantLoader, Loader
from custom_components.haeo.data.loader.extractors import EntityMetadata

from .fields import Default, Direction, FieldMeta, NumberLimits
from .params import SchemaParams

__all__ = [
    "Default",
    "Direction",
    "EntityMetadata",
    "FieldMeta",
    "NumberLimits",
    "available",
    "get_data_defaults",
    "get_field_meta",
    "get_loader_instance",
    "get_schema_defaults",
    "load",
    "schema_for_type",
]


if TYPE_CHECKING:
    from custom_components.haeo.elements import (
        ElementConfigData,
        ElementConfigSchema,
        ElementRegistryEntry,
        ElementType,
    )

T = TypeVar("T")


def _get_registry_entry(element_type: "ElementType") -> "ElementRegistryEntry":
    """Look up the registry entry for an element type."""

    # Import here to avoid circular import
    from custom_components.haeo.elements import ELEMENT_TYPES  # noqa: PLC0415

    return ELEMENT_TYPES[element_type]


def get_field_meta(field_name: str, config_class: type) -> FieldMeta | None:
    """Extract the FieldMeta instance from a field's annotation.

    This inspects the type annotations of a Data mode TypedDict to find the
    FieldMeta instance.

    Args:
        field_name: Name of the field
        config_class: TypedDict config class (Data mode)

    Returns:
        The FieldMeta instance, or None if not found

    """
    hints = get_type_hints(config_class, include_extras=True)
    field_type = hints[field_name]

    # Handle NotRequired wrapper
    origin = get_origin(field_type)
    if origin is not None and origin.__name__ == "NotRequired":
        field_type = get_args(field_type)[0]

    # Extract FieldMeta from Annotated type
    if get_origin(field_type) is Annotated:
        for meta in field_type.__metadata__:
            if isinstance(meta, FieldMeta):
                return meta

    return None


def get_schema_defaults(schema_class: type) -> dict[str, Any]:
    """Extract schema default values from a ConfigSchema type.

    Iterates through field annotations and extracts Default.schema values
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
        # Handle NotRequired wrapper
        origin = get_origin(field_type)
        if origin is not None and hasattr(origin, "__name__") and origin.__name__ == "NotRequired":
            inner_type = get_args(field_type)[0]
        else:
            inner_type = field_type

        # Extract Default from Annotated type
        if get_origin(inner_type) is Annotated:
            for meta in inner_type.__metadata__:
                if isinstance(meta, Default) and meta.schema is not None:
                    defaults[field_name] = meta.schema
                    break

    return defaults


def get_data_defaults(data_class: type) -> dict[str, float | bool]:
    """Extract data default values from a ConfigData type.

    Iterates through field annotations and extracts Default.data_default values
    for use when loading configs where a field was not configured.

    Args:
        data_class: TypedDict config data class (Data mode)

    Returns:
        Dictionary mapping field names to their data default values.
        Only fields with Default markers (with data or schema defaults) are included.

    """
    defaults: dict[str, float | bool] = {}
    hints = get_type_hints(data_class, include_extras=True)

    for field_name, field_type in hints.items():
        # Handle NotRequired wrapper
        origin = get_origin(field_type)
        if origin is not None and hasattr(origin, "__name__") and origin.__name__ == "NotRequired":
            inner_type = get_args(field_type)[0]
        else:
            inner_type = field_type

        # Extract Default from Annotated type
        if get_origin(inner_type) is Annotated:
            for meta in inner_type.__metadata__:
                if isinstance(meta, Default):
                    data_default = meta.data_default
                    if data_default is not None:
                        defaults[field_name] = data_default
                    break

    return defaults


def get_loader_instance(field_name: str, config_class: type) -> Loader:
    """Extract the loader instance from a field's FieldMeta annotation.

    This inspects the type annotations of a Data mode TypedDict to find the
    FieldMeta instance, which contains the typed loader instance.

    Args:
        field_name: Name of the field
        config_class: TypedDict config class (Data mode)

    Returns:
        The loader instance

    """
    field_meta = get_field_meta(field_name, config_class)
    return field_meta.loader if field_meta else ConstantLoader[Any](object)


def available(
    config: "ElementConfigSchema",
    **kwargs: Any,
) -> bool:
    """Check if all fields in a config are available for loading.

    Args:
        config: Schema mode config (with entity IDs)
        **kwargs: Additional arguments passed to loader.available() (e.g., hass, forecast_times)

    Returns:
        True if all required fields are available for loading

    """
    # Look up data class from element type
    # Element type must be valid since it was validated during config flow
    element_type = config["element_type"]
    data_config_class = _get_registry_entry(element_type).data

    hints = get_type_hints(data_config_class, include_extras=True)

    for field_name in hints:
        # Skip metadata fields
        if field_name in ("element_type", "name"):
            continue

        field_value = config.get(field_name)
        if field_value is None:
            continue  # Skip optional fields that weren't provided

        # Get loader and check availability
        loader_instance = get_loader_instance(field_name, data_config_class)
        if not loader_instance.available(value=field_value, **kwargs):
            return False

    return True


async def load(
    config: "ElementConfigSchema", hass: HomeAssistant, forecast_times: Sequence[float]
) -> "ElementConfigData":
    """Load all fields in a config, converting from Schema to Data mode.

    Args:
        config: Schema mode config (with entity IDs)
        hass: Home Assistant instance
        forecast_times: Time intervals for data aggregation.

    Returns:
        Data mode config (with loaded values)

    """
    # Look up data class from element type
    # Element type must be valid since it was validated during config flow
    element_type = config["element_type"]
    data_config_class = _get_registry_entry(element_type).data

    hints = get_type_hints(data_config_class, include_extras=True)
    data_defaults = get_data_defaults(data_config_class)
    loaded: dict[str, Any] = {}
    n_periods = len(forecast_times) - 1

    for field_name, field_type in hints.items():
        field_value = config.get(field_name)

        # If field is not configured, check for data default
        if field_value is None:
            data_default = data_defaults.get(field_name)
            if data_default is not None:
                # Check if the field expects a list/tuple (time series) or scalar
                # Unwrap NotRequired and Annotated to get the base type
                base_type = _unwrap_type(field_type)
                origin = get_origin(base_type)
                if origin is list or origin is tuple:
                    # Time series field - expand default to tuple
                    loaded[field_name] = tuple([data_default] * n_periods)
                else:
                    # Scalar field - use default directly
                    loaded[field_name] = data_default
            continue  # Skip fields with no value and no default

        # Get loader and load the field
        loader_instance = get_loader_instance(field_name, data_config_class)
        loaded[field_name] = await loader_instance.load(value=field_value, hass=hass, forecast_times=forecast_times)

    return cast("ElementConfigData", loaded)


def _unwrap_type(field_type: Any) -> Any:
    """Unwrap NotRequired and Annotated wrappers to get the base type."""
    # Handle NotRequired wrapper
    origin = get_origin(field_type)
    if origin is not None and hasattr(origin, "__name__") and origin.__name__ == "NotRequired":
        field_type = get_args(field_type)[0]

    # Handle Annotated wrapper
    if get_origin(field_type) is Annotated:
        field_type = get_args(field_type)[0]

    return field_type


def _get_annotated_fields(cls: type) -> dict[str, tuple[FieldMeta, bool]]:
    """Get the annotated fields for a TypedDict type.

    Returns:
        dict[field_name, (metadata, is_optional)]
        where is_optional indicates if the field has NotRequired

    """
    hints = get_type_hints(cls, include_extras=True)
    annotated: dict[str, tuple[FieldMeta, bool]] = {}

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

        # Unwrap Optional[...] (Union[..., None])
        if get_origin(unwrapped_tp) is Union:
            args = [a for a in get_args(unwrapped_tp) if a is not type(None)]
            if len(args) == 1:
                unwrapped_tp = args[0]
                is_optional = True
            elif len(args) > 1:
                # For Union types, try to find the first type with Annotated metadata
                for arg in args:
                    if get_origin(arg) is Annotated:
                        unwrapped_tp = arg
                        break

        # Extract Annotated metadata - search for FieldMeta in all metadata items
        if get_origin(unwrapped_tp) is Annotated:
            args = get_args(unwrapped_tp)
            # Skip the first arg (the base type), then find FieldMeta
            for arg in args[1:]:
                if isinstance(arg, FieldMeta):
                    annotated[field_name] = (arg, is_optional)
                    break

    return annotated


def schema_for_type(cls: type, **schema_params: Unpack[SchemaParams]) -> vol.Schema:
    """Create a schema for a TypedDict type.

    Args:
        cls: The TypedDict class to create schema for (Schema mode)
        **schema_params: Schema parameters passed to field validators

    Returns:
        Voluptuous schema

    Note:
        Sensor fields are made optional in the schema only if they have a data
        default defined. Sensor fields without data defaults remain required.
        The required/optional distinction for sensor fields with defaults
        affects whether the corresponding input entity starts enabled or disabled,
        not whether the user must provide a value in the config flow.

    """
    # Get the corresponding Data class to check for data defaults
    # Schema class name ends with "Schema", Data class ends with "Data"
    data_cls_name = cls.__name__.replace("Schema", "Data")
    data_cls = getattr(cls.__module__.split(".")[-1], data_cls_name, None) if hasattr(cls, "__module__") else None

    # Try to get data class from module
    if data_cls is None:
        try:
            module = importlib.import_module(cls.__module__)
            data_cls = getattr(module, data_cls_name, None)
        except (ImportError, AttributeError):
            data_cls = None

    # Get data defaults if we found the data class
    data_defaults = get_data_defaults(data_cls) if data_cls else {}

    annotated_fields = _get_annotated_fields(cls)
    schema: dict[vol.Required | vol.Optional, vol.All] = {}
    for field, (meta, is_optional) in annotated_fields.items():
        validator = meta.create_schema(**schema_params)
        # Sensor fields are optional only if they have a data default
        has_data_default = field in data_defaults
        is_schema_optional = is_optional or (meta.field_type == "sensor" and has_data_default)
        schema_key = (vol.Optional if is_schema_optional else vol.Required)(field)
        schema[schema_key] = validator

    return vol.Schema(schema)
