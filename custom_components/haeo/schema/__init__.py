"""Schema utilities for flattening and reconstructing HAEO type configurations."""

from typing import TYPE_CHECKING, Annotated, Any, TypeVar, Union, get_args, get_origin, get_type_hints
from typing import get_origin as typing_get_origin

import voluptuous as vol

from custom_components.haeo.data.loader import ConstantLoader

from .fields import FieldMeta

if TYPE_CHECKING:
    from custom_components.haeo.data.loader import Loader
    from custom_components.haeo.types import ElementConfigData, ElementConfigSchema

# Import at module level for runtime use
from custom_components.haeo.types import ELEMENT_TYPES

T = TypeVar("T")


def get_loader_instance(field_name: str, config_class: type) -> "Loader":
    """Extract the loader instance from a field's FieldMeta annotation.

    This inspects the type annotations of a Data mode TypedDict to find the
    FieldMeta instance, which contains the typed loader instance.

    Args:
        field_name: Name of the field
        config_class: TypedDict config class (Data mode)

    Returns:
        The loader instance (ConstantLoader, SensorLoader, ForecastLoader, etc.)

    """
    hints = get_type_hints(config_class, include_extras=True)

    if field_name not in hints:
        return ConstantLoader[Any]()  # Default fallback

    field_type = hints[field_name]

    # Handle NotRequired wrapper
    if get_origin(field_type).__name__ == "NotRequired":
        field_type = get_args(field_type)[0]

    # Extract FieldMeta from Annotated type
    if get_origin(field_type) is Annotated:
        for meta in field_type.__metadata__:
            if isinstance(meta, FieldMeta):
                return meta.loader

    # Fallback
    return ConstantLoader[Any]()


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
    element_types = ELEMENT_TYPES.get(config["element_type"])
    if not element_types:
        return False
    _, data_config_class, _ = element_types

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
        if not loader_instance.available(value=field_value, **kwargs):  # type: ignore[arg-type]
            return False

    return True


async def load(
    config: "ElementConfigSchema",
    **kwargs: Any,
) -> "ElementConfigData":
    """Load all fields in a config, converting from Schema to Data mode.

    Args:
        config: Schema mode config (with entity IDs)
        **kwargs: Additional arguments passed to loader.load() (e.g., hass, forecast_times)

    Returns:
        Data mode config (with loaded values)

    """
    # Look up data class from element type
    element_types = ELEMENT_TYPES.get(config["element_type"])
    if not element_types:
        msg = f"Unknown element type: {config['element_type']}"
        raise ValueError(msg)
    _, data_config_class, _ = element_types

    hints = get_type_hints(data_config_class, include_extras=True)
    loaded: dict[str, Any] = {}

    for field_name in hints:
        field_value = config.get(field_name)

        # Pass through metadata fields and None values
        if field_value is None and field_name not in ("element_type", "name"):
            continue  # Skip optional fields

        # Get loader and load the field
        loader_instance = get_loader_instance(field_name, data_config_class)
        loaded[field_name] = await loader_instance.load(value=field_value, **kwargs)  # type: ignore[arg-type]

    return loaded  # type: ignore[return-value]


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
        if typing_get_origin(field_tp).__name__ == "NotRequired":
            field_tp = get_args(field_tp)[0]
            is_optional = True

        # Unwrap Optional[...] (Union[..., None])
        if get_origin(field_tp) is Union:
            args = [a for a in get_args(field_tp) if a is not type(None)]
            if len(args) == 1:
                field_tp = args[0]
                is_optional = True
            elif len(args) > 1:
                # For Union types, try to find the first type with Annotated metadata
                for arg in args:
                    if get_origin(arg) is Annotated:
                        field_tp = arg
                        break

        # Extract Annotated metadata
        if get_origin(field_tp) is Annotated:
            *_, meta = get_args(field_tp)

            if isinstance(meta, FieldMeta):
                annotated[field_name] = (meta, is_optional)

    return annotated


def schema_for_type(cls: type, **kwargs: Any) -> vol.Schema:
    """Create a schema for a TypedDict type."""
    annotated_fields = _get_annotated_fields(cls)

    schema = {}
    for field, (meta, is_optional) in annotated_fields.items():
        for k, s in meta.create_schema(**kwargs).items():
            key = f"{field}_{k}"
            schema_key = (vol.Optional if is_optional else vol.Required)(key)
            schema[schema_key] = s

    return vol.Schema(schema)


def data_to_config[T](cls: type[T], data: dict[str, Any], **kwargs: Any) -> T:
    """Convert flattened data to a TypedDict configuration.

    Args:
        cls: The TypedDict configuration class
        data: The flattened data from config flow
        **kwargs: Additional keyword arguments (e.g., participants list)

    Returns:
        A dictionary matching the TypedDict schema

    """
    output: dict[str, Any] = {}

    # Add element_type from data if present
    if "type" in data:
        output["element_type"] = data["type"]
    elif "element_type" in data:
        output["element_type"] = data["element_type"]

    for field, (meta, is_optional) in _get_annotated_fields(cls).items():
        schema_keys = meta.create_schema(**kwargs).keys()
        field_data = {k: data.get(f"{field}_{k}") for k in schema_keys}

        # Check if field was provided
        has_data = any(v is not None for v in field_data.values())

        # For optional fields that weren't provided, skip them
        if is_optional and not has_data:
            continue

        # For constant, sensor, and forecast fields, extract just the value
        if meta.field_type[1] in ("constant", "sensor", "forecast"):
            if "value" in field_data and field_data["value"] is not None:
                output[field] = field_data["value"]
        # For live_forecast fields, preserve the dictionary structure
        elif meta.field_type[1] == "live_forecast":
            live_data = field_data.get("live")
            forecast_data = field_data.get("forecast")
            if live_data is not None or forecast_data is not None:
                output[field] = {"live": live_data or [], "forecast": forecast_data or []}
        else:
            # For other field types, use the field_data as-is
            output[field] = field_data

    return output  # type: ignore[return-value]
