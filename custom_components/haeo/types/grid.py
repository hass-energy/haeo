"""Grid element configuration for HAEO integration."""

from typing import Any, Literal, NotRequired, TypedDict

from custom_components.haeo.schema.fields import (
    NameFieldData,
    NameFieldSchema,
    PowerFieldData,
    PowerFieldSchema,
    PricesSensorsAndForecastsFieldData,
    PricesSensorsAndForecastsFieldSchema,
)


class GridConfigSchema(TypedDict):
    """Grid element configuration."""

    element_type: Literal["grid"]
    name: NameFieldSchema
    import_price: PricesSensorsAndForecastsFieldSchema
    export_price: PricesSensorsAndForecastsFieldSchema

    # Optional fields
    import_limit: NotRequired[PowerFieldSchema]
    export_limit: NotRequired[PowerFieldSchema]


class GridConfigData(TypedDict):
    """Grid element configuration."""

    element_type: Literal["grid"]
    name: NameFieldData
    import_price: PricesSensorsAndForecastsFieldData
    export_price: PricesSensorsAndForecastsFieldData

    # Optional fields
    import_limit: NotRequired[PowerFieldData]
    export_limit: NotRequired[PowerFieldData]


GRID_CONFIG_DEFAULTS: dict[str, Any] = {}
