"""Grid element configuration for HAEO integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.model import ModelOutputName
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
from custom_components.haeo.model.const import OUTPUT_TYPE_POWER
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

GRID_OUTPUT_NAMES: Final[frozenset[GridOutputName]] = frozenset(
    (
        GRID_POWER_IMPORT := "grid_power_import",
        GRID_POWER_EXPORT := "grid_power_export",
        GRID_POWER_MAX_IMPORT := "grid_power_max_import",
        GRID_POWER_MAX_EXPORT := "grid_power_max_export",
        GRID_PRICE_IMPORT := "grid_price_import",
        GRID_PRICE_EXPORT := "grid_price_export",
        # Shadow prices
        GRID_POWER_MAX_IMPORT_PRICE := "grid_power_max_import_price",
        GRID_POWER_MAX_EXPORT_PRICE := "grid_power_max_export_price",
    )
)

type GridDeviceName = Literal["grid"]

GRID_DEVICE_NAMES: Final[frozenset[GridDeviceName]] = frozenset(
    (GRID_DEVICE_GRID := ELEMENT_TYPE,),
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
        # Create a connection from system node to grid
        {
            "element_type": "connection",
            "name": f"{config['name']}:connection",
            "source": config["name"],
            "target": config["connection"],
            "max_power_source_target": config.get("import_limit"),  # source_target is grid to system (IMPORT)
            "max_power_target_source": config.get("export_limit"),  # target_source is system to grid (EXPORT)
            "price_source_target": config["import_price"],
            "price_target_source": [-p for p in config["export_price"]],  # Negate export because exporting earns money
        },
    ]


def outputs(
    name: str, model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]], _config: GridConfigData
) -> Mapping[GridDeviceName, Mapping[GridOutputName, OutputData]]:
    """Map model outputs to grid-specific output names."""

    connection = model_outputs[f"{name}:connection"]

    grid_outputs: dict[GridOutputName, OutputData] = {}

    # source_target = grid to system = IMPORT
    # target_source = system to grid = EXPORT
    grid_outputs[GRID_POWER_EXPORT] = replace(connection[CONNECTION_POWER_TARGET_SOURCE], type=OUTPUT_TYPE_POWER)
    grid_outputs[GRID_POWER_IMPORT] = replace(connection[CONNECTION_POWER_SOURCE_TARGET], type=OUTPUT_TYPE_POWER)

    # Output the given inputs if they exist
    if CONNECTION_POWER_MAX_TARGET_SOURCE in connection:
        grid_outputs[GRID_POWER_MAX_EXPORT] = connection[CONNECTION_POWER_MAX_TARGET_SOURCE]
        grid_outputs[GRID_POWER_MAX_EXPORT_PRICE] = connection[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE]
    if CONNECTION_POWER_MAX_SOURCE_TARGET in connection:
        grid_outputs[GRID_POWER_MAX_IMPORT] = connection[CONNECTION_POWER_MAX_SOURCE_TARGET]
        grid_outputs[GRID_POWER_MAX_IMPORT_PRICE] = connection[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET]

    # Negate export price values for display (so they appear positive)
    export_price_data = connection[CONNECTION_PRICE_TARGET_SOURCE]
    grid_outputs[GRID_PRICE_EXPORT] = replace(export_price_data, values=[-v for v in export_price_data.values])
    grid_outputs[GRID_PRICE_IMPORT] = replace(connection[CONNECTION_PRICE_SOURCE_TARGET])

    return {GRID_DEVICE_GRID: grid_outputs}
