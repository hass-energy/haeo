"""Loader dispatch module for field type-specific data loading."""

from collections.abc import Callable, Coroutine
from dataclasses import fields
from typing import Any, cast, get_origin

from homeassistant.core import HomeAssistant

from custom_components.haeo.const import (
    FIELD_TYPE_CONSTANT,
    FIELD_TYPE_FORECAST,
    FIELD_TYPE_LIVE_FORECAST,
    FIELD_TYPE_SENSOR,
)
from custom_components.haeo.data.loader import (
    constant_loader,
    forecast_and_sensor_loader,
    forecast_loader,
    sensor_loader,
)
from custom_components.haeo.schema.fields import FieldMeta


def _get_property_type(field_name: str, config_class: type) -> str:
    """Determine the property type for a field in a config class.

    This function inspects the field annotations to determine if a field
    is a sensor, forecast, or constant type.

    Args:
        field_name: Name of the field
        config_class: Config class

    Returns:
        The property type for the field

    """

    # Get the field from the config class
    config_fields = {f.name: f for f in fields(config_class)}
    if field_name not in config_fields:
        return FIELD_TYPE_CONSTANT  # Default fallback

    # Check if the field has type annotations with metadata
    field_type_hints = getattr(config_class, "__annotations__", {})
    if field_name in field_type_hints:
        field_type = field_type_hints[field_name]
        # Check if it's an Annotated type with FieldMeta

        if get_origin(field_type) is type(field_type):  # Simple type
            return FIELD_TYPE_CONSTANT
        if hasattr(field_type, "__metadata__"):  # Annotated type
            for meta in field_type.__metadata__:
                if isinstance(meta, FieldMeta):
                    # Check the field_type tuple (device_class, field_type)
                    _, field_type_str = meta.field_type
                    return field_type_str

    return FIELD_TYPE_CONSTANT


def available(*, hass: HomeAssistant, field_name: str, config_class: type, value: Any, **kwargs: Any) -> bool:
    """Return True if the field is available.

    Args:
        hass: Home Assistant instance
        field_name: Name of the field
        config_class: Config class
        value: Value of the field
        **kwargs: Additional keyword arguments

    """
    pt = _get_property_type(field_name, config_class)

    loader_fn = cast(
        "Callable[..., bool]",
        {
            FIELD_TYPE_CONSTANT: constant_loader.available,
            FIELD_TYPE_SENSOR: sensor_loader.available,
            FIELD_TYPE_FORECAST: forecast_loader.available,
            FIELD_TYPE_LIVE_FORECAST: forecast_and_sensor_loader.available,
        }[pt],
    )

    return loader_fn(hass=hass, value=value, **kwargs)


async def load(*, hass: HomeAssistant, field_name: str, config_class: type, value: Any, **kwargs: Any) -> Any:
    """Load the field.

    Args:
        hass: Home Assistant instance
        field_name: Name of the field
        config_class: Config class
        value: Value of the field
        **kwargs: Additional keyword arguments

    """
    pt = _get_property_type(field_name, config_class)

    loader_fn = cast(
        "Callable[..., Coroutine[Any, Any, Any]]",
        {
            FIELD_TYPE_CONSTANT: constant_loader.load,
            FIELD_TYPE_SENSOR: sensor_loader.load,
            FIELD_TYPE_FORECAST: forecast_loader.load,
            FIELD_TYPE_LIVE_FORECAST: forecast_and_sensor_loader.load,
        }[pt],
    )

    return await loader_fn(hass=hass, value=value, **kwargs)
