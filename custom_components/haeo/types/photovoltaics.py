"""Photovoltaics element configuration for HAEO integration."""

from typing import Any, Literal, NotRequired, TypedDict

from custom_components.haeo.schema.fields import (
    BooleanFieldData,
    BooleanFieldSchema,
    NameFieldData,
    NameFieldSchema,
    PowerForecastsFieldData,
    PowerForecastsFieldSchema,
    PriceFieldData,
    PriceFieldSchema,
)


class PhotovoltaicsConfigSchema(TypedDict):
    """Photovoltaics element configuration."""

    element_type: Literal["photovoltaics"]
    name: NameFieldSchema
    forecast: PowerForecastsFieldSchema

    # Optional fields
    price_production: NotRequired[PriceFieldSchema]
    curtailment: NotRequired[BooleanFieldSchema]


class PhotovoltaicsConfigData(TypedDict):
    """Photovoltaics element configuration."""

    element_type: Literal["photovoltaics"]
    name: NameFieldData
    forecast: PowerForecastsFieldData

    # Optional fields
    price_production: NotRequired[PriceFieldData]
    curtailment: NotRequired[BooleanFieldData]


PHOTOVOLTAICS_CONFIG_DEFAULTS: dict[str, Any] = {
    "curtailment": False,
}


def model_description(config: PhotovoltaicsConfigData) -> str:  # noqa: ARG001
    """Generate model description string for photovoltaics element.

    Args:
        config: Photovoltaics configuration data.

    Returns:
        Formatted model description string.

    """
    return "Solar"
