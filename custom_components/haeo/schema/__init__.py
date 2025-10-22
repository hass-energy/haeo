"""Schema utilities for flattening and reconstructing HAEO type configurations."""

from collections.abc import Mapping
from typing import TYPE_CHECKING, Annotated, Any, TypeVar, Union, cast, get_args, get_origin, get_type_hints
from typing import get_origin as typing_get_origin

from homeassistant.core import HomeAssistant
import voluptuous as vol

from custom_components.haeo.data.loader import ConstantLoader, Loader

from .fields import FieldMeta, FieldValidator

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

    if element_type not in ELEMENT_TYPES:
        msg = f"Invalid element type {element_type} - config flow validation failed"
        raise RuntimeError(msg)
    return ELEMENT_TYPES[element_type]


def get_loader_instance(field_name: str, config_class: type) -> Loader:
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
        msg = f"Field {field_name} not found in config class {config_class.__name__}"
        raise RuntimeError(msg)

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
    return ConstantLoader[Any](object)


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


async def load(config: "ElementConfigSchema", hass: HomeAssistant, forecast_times: list[int]) -> "ElementConfigData":
    """Load all fields in a config, converting from Schema to Data mode.

    Args:
        config: Schema mode config (with entity IDs)
        hass: Home Assistant instance
        forecast_times: Time intervals for data aggregation

    Returns:
        Data mode config (with loaded values)

    """
    # Look up data class from element type
    # Element type must be valid since it was validated during config flow
    element_type = config["element_type"]
    data_config_class = _get_registry_entry(element_type).data

    hints = get_type_hints(data_config_class, include_extras=True)
    loaded: dict[str, Any] = {}

    for field_name in hints:
        field_value = config.get(field_name)

        # Pass through metadata fields and None values
        if field_value is None:
            continue  # Skip optional fields

        # Get loader and load the field
        loader_instance = get_loader_instance(field_name, data_config_class)
        loaded[field_name] = await loader_instance.load(value=field_value, hass=hass, forecast_times=forecast_times)

    return cast("ElementConfigData", loaded)


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
        if typing_get_origin(unwrapped_tp).__name__ == "NotRequired":
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

        # Extract Annotated metadata
        if get_origin(unwrapped_tp) is Annotated:
            *_, meta = get_args(unwrapped_tp)

            if isinstance(meta, FieldMeta):
                annotated[field_name] = (meta, is_optional)

    return annotated


def schema_for_type(cls: type, defaults: dict[str, Any] | None = None, **kwargs: Any) -> vol.Schema:
    """Create a schema for a TypedDict type.

    Args:
        cls: The TypedDict class to create schema for
        defaults: Optional dict of default values to pre-populate (flattened format)
        **kwargs: Additional arguments passed to field validators

    Returns:
        Voluptuous schema with optional defaults

    """
    annotated_fields = _get_annotated_fields(cls)
    defaults = defaults or {}

    schema: dict[vol.Required | vol.Optional, FieldValidator] = {}
    for field, (meta, is_optional) in annotated_fields.items():
        validator = meta.create_schema(**kwargs)

        if isinstance(validator, Mapping):
            for subkey, subvalidator in validator.items():
                key = f"{field}:{subkey}"
                default_value = defaults.get(key, vol.UNDEFINED)
                schema_key = (vol.Optional if is_optional else vol.Required)(key, default=default_value)
                schema[schema_key] = subvalidator
        else:
            key = field
            default_value = defaults.get(key, vol.UNDEFINED)
            schema_key = (vol.Optional if is_optional else vol.Required)(key, default=default_value)
            schema[schema_key] = validator

    return vol.Schema(schema)


def unflatten(data: dict[str, Any]) -> dict[str, Any]:
    """Convert flattened delimited dictionary to to structured dictionary."""
    output: dict[str, Any] = {}

    # Unflatten data treating ":" as delimiter
    for k, v in data.items():
        ks = k.split(":")
        if len(ks) > 1:
            output.setdefault(ks[0], {})[ks[1]] = v
        else:
            output[k] = v

    return output


def flatten(config: dict[str, Any]) -> dict[str, Any]:
    """Convert structured dictionary to flattened delimited dictionary."""

    output: dict[str, Any] = {}
    for k, v in config.items():
        if isinstance(v, dict):
            for subk, subv in v.items():
                output[f"{k}:{subk}"] = subv
        else:
            output[k] = v

    return output
