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


def model_description(config: GridConfigData) -> str:
    """Generate device model string from grid configuration."""
    import_kw = config.get("import_limit")
    export_kw = config.get("export_limit")

    if import_kw is not None or export_kw is not None:
        parts = []
        if import_kw is not None:
            parts.append(f"Import {import_kw:.1f}kW")
        if export_kw is not None:
            parts.append(f"Export {export_kw:.1f}kW")
        return f"Grid {', '.join(parts)}"
    return "Grid Connection"
