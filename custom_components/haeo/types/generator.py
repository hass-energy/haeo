"""Generator element configuration for HAEO integration."""

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


class GeneratorConfigSchema(TypedDict):
    """Generator element configuration."""

    element_type: Literal["generator"]
    name: NameFieldSchema
    forecast: PowerForecastsFieldSchema

    # Optional fields
    price_production: NotRequired[PriceFieldSchema]
    curtailment: NotRequired[BooleanFieldSchema]


class GeneratorConfigData(TypedDict):
    """Generator element configuration."""

    element_type: Literal["generator"]
    name: NameFieldData
    forecast: PowerForecastsFieldData

    # Optional fields
    price_production: NotRequired[PriceFieldData]
    curtailment: NotRequired[BooleanFieldData]


GENERATOR_CONFIG_DEFAULTS: dict[str, Any] = {
    "curtailment": False,
}
