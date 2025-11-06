"""Grid element configuration for HAEO integration."""

from typing import Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.schema.fields import (
    NameFieldData,
    NameFieldSchema,
    PowerFieldData,
    PowerFieldSchema,
    PriceSensorsFieldData,
    PriceSensorsFieldSchema,
)

ELEMENT_TYPE: Final = "grid"

CONF_IMPORT_PRICE: Final = "import_price"
CONF_EXPORT_PRICE: Final = "export_price"
CONF_IMPORT_LIMIT: Final = "import_limit"
CONF_EXPORT_LIMIT: Final = "export_limit"
CONF_IMPORT_PRICE_FORECAST: Final = "import_price_forecast"
CONF_EXPORT_PRICE_FORECAST: Final = "export_price_forecast"


class GridConfigSchema(TypedDict):
    """Grid element configuration."""

    element_type: Literal["grid"]
    name: NameFieldSchema
    import_price: PriceSensorsFieldSchema
    export_price: PriceSensorsFieldSchema

    # Optional fields
    import_limit: NotRequired[PowerFieldSchema]
    export_limit: NotRequired[PowerFieldSchema]


class GridConfigData(TypedDict):
    """Grid element configuration."""

    element_type: Literal["grid"]
    name: NameFieldData
    import_price: PriceSensorsFieldData
    export_price: PriceSensorsFieldData

    # Optional fields
    import_limit: NotRequired[PowerFieldData]
    export_limit: NotRequired[PowerFieldData]


CONFIG_DEFAULTS: dict[str, Any] = {}


def model_description(config: GridConfigSchema) -> str:
    """Generate device model string from grid configuration."""
    import_kw = config.get(CONF_IMPORT_LIMIT)
    export_kw = config.get(CONF_EXPORT_LIMIT)

    # Use type guard to check if at least one limit is set
    if import_kw is not None or export_kw is not None:
        parts: list[str] = []
        if import_kw is not None:
            parts.append(f"Import {import_kw:.1f}kW")
        if export_kw is not None:
            parts.append(f"Export {export_kw:.1f}kW")
        return f"Grid {', '.join(parts)}"
    return "Grid Connection"
