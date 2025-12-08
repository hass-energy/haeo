"""Grid element configuration for HAEO integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.model import OutputName as ModelOutputName
from custom_components.haeo.model.connection import (
    CONNECTION_POWER_MAX_SOURCE_TARGET,
    CONNECTION_POWER_MAX_TARGET_SOURCE,
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_PRICE_SOURCE_TARGET,
    CONNECTION_PRICE_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
)
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.schema.fields import (
    ElementNameFieldSchema,
    NameFieldData,
    NameFieldSchema,
    PowerFieldData,
    PowerFieldSchema,
    PriceSensorsFieldData,
    PriceSensorsFieldSchema,
)

ELEMENT_TYPE: Final = "grid"

# Configuration field names
CONF_IMPORT_PRICE: Final = "import_price"
CONF_EXPORT_PRICE: Final = "export_price"
CONF_IMPORT_LIMIT: Final = "import_limit"
CONF_EXPORT_LIMIT: Final = "export_limit"
CONF_IMPORT_PRICE_FORECAST: Final = "import_price_forecast"
CONF_EXPORT_PRICE_FORECAST: Final = "export_price_forecast"
CONF_CONNECTION: Final = "connection"

# Grid-specific sensor names (for translation/output mapping)
type GridOutputName = Literal[
    "grid_power_import",
    "grid_power_export",
    "grid_power_max_import",
    "grid_power_max_export",
    "grid_price_import",
    "grid_price_export",
    "grid_power_max_import_price",
    "grid_power_max_export_price",
]
GRID_POWER_IMPORT: Final = "grid_power_import"
GRID_POWER_EXPORT: Final = "grid_power_export"
GRID_POWER_MAX_IMPORT: Final = "grid_power_max_import"
GRID_POWER_MAX_EXPORT: Final = "grid_power_max_export"
GRID_PRICE_IMPORT: Final = "grid_price_import"
GRID_PRICE_EXPORT: Final = "grid_price_export"
GRID_POWER_MAX_IMPORT_PRICE: Final = "grid_power_max_import_price"
GRID_POWER_MAX_EXPORT_PRICE: Final = "grid_power_max_export_price"

GRID_OUTPUT_NAMES: Final[frozenset[GridOutputName]] = frozenset(
    (
        GRID_POWER_IMPORT,
        GRID_POWER_EXPORT,
        GRID_POWER_MAX_IMPORT,
        GRID_POWER_MAX_EXPORT,
        GRID_PRICE_IMPORT,
        GRID_PRICE_EXPORT,
        # Shadow prices
        GRID_POWER_MAX_IMPORT_PRICE,
        GRID_POWER_MAX_EXPORT_PRICE,
    )
)


class GridConfigSchema(TypedDict):
    """Grid element configuration."""

    element_type: Literal["grid"]
    name: NameFieldSchema
    connection: ElementNameFieldSchema  # Connection ID that grid connects to
    import_price: PriceSensorsFieldSchema
    export_price: PriceSensorsFieldSchema

    # Optional fields
    import_limit: NotRequired[PowerFieldSchema]
    export_limit: NotRequired[PowerFieldSchema]


class GridConfigData(TypedDict):
    """Grid element configuration."""

    element_type: Literal["grid"]
    name: NameFieldData
    connection: ElementNameFieldSchema  # Connection ID that grid connects to
    import_price: PriceSensorsFieldData
    export_price: PriceSensorsFieldData

    # Optional fields
    import_limit: NotRequired[PowerFieldData]
    export_limit: NotRequired[PowerFieldData]


CONFIG_DEFAULTS: dict[str, Any] = {}


def create_model_elements(config: GridConfigData) -> list[dict[str, Any]]:
    """Create model elements for Grid configuration."""

    return [
        # Create SourceSink for the grid (both source and sink - can import and export)
        {"element_type": "source_sink", "name": config["name"], "is_source": True, "is_sink": True},
        # Create a connection from the grid to the specified node
        {
            "element_type": "connection",
            "name": f"{config['name']}:connection",
            "source": config["name"],
            "target": config["connection"],
            "max_power_source_target": config.get("import_limit"),
            "max_power_target_source": config.get("export_limit"),
            "price_source_target": config.get("import_price"),
            "price_target_source": config.get("export_price"),
        },
    ]


def outputs(
    name: str, model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
) -> dict[str, dict[GridOutputName, OutputData]]:
    """Map model outputs to grid-specific output names."""

    connection = model_outputs[f"{name}:connection"]

    grid_outputs: dict[GridOutputName, OutputData] = {}

    # This will be identical to the source/sink power in/out outputs
    grid_outputs[GRID_POWER_EXPORT] = connection[CONNECTION_POWER_TARGET_SOURCE]
    grid_outputs[GRID_POWER_IMPORT] = connection[CONNECTION_POWER_SOURCE_TARGET]

    # Output the given inputs if they exist
    if CONNECTION_POWER_MAX_SOURCE_TARGET in connection:
        grid_outputs[GRID_POWER_MAX_IMPORT] = connection[CONNECTION_POWER_MAX_SOURCE_TARGET]
        grid_outputs[GRID_POWER_MAX_IMPORT_PRICE] = connection[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET]
    if CONNECTION_POWER_MAX_TARGET_SOURCE in connection:
        grid_outputs[GRID_POWER_MAX_EXPORT] = connection[CONNECTION_POWER_MAX_TARGET_SOURCE]
        grid_outputs[GRID_POWER_MAX_EXPORT_PRICE] = connection[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE]

    grid_outputs[GRID_PRICE_EXPORT] = connection[CONNECTION_PRICE_TARGET_SOURCE]
    grid_outputs[GRID_PRICE_IMPORT] = connection[CONNECTION_PRICE_SOURCE_TARGET]

    return {name: grid_outputs}
