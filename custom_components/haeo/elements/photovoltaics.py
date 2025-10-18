"""Photovoltaics element configuration for HAEO integration."""

from typing import Any, Final, Literal, NotRequired, TypedDict

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

ELEMENT_TYPE: Final = "photovoltaics"

CONF_FORECAST: Final = "forecast"
CONF_PRICE_PRODUCTION: Final = "price_production"
CONF_PRICE_CONSUMPTION: Final = "price_consumption"
CONF_CURTAILMENT: Final = "curtailment"


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


CONFIG_DEFAULTS: dict[str, Any] = {
    CONF_CURTAILMENT: False,
}


def model_description(_config: PhotovoltaicsConfigData) -> str:
    """Generate model description string for photovoltaics element.

    Args:
        _config: Photovoltaics configuration data.

    Returns:
        Formatted model description string.

    """
    return "Solar"
