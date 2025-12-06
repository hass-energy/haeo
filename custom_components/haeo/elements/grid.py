"""Grid element configuration for HAEO integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.source_sink import (
    SOURCE_SINK_POWER_BALANCE,
    SOURCE_SINK_POWER_IN,
    SOURCE_SINK_POWER_OUT,
)
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
GRID_POWER_IMPORT: Final = "grid_power_import"
GRID_POWER_EXPORT: Final = "grid_power_export"
GRID_POWER_BALANCE: Final = "grid_power_balance"


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


def create_model_elements(
    config: GridConfigData,
    period: float,  # noqa: ARG001
    n_periods: int,  # noqa: ARG001
) -> list[dict[str, Any]]:
    """Create model elements for Grid configuration.

    Returns a list of element configurations that should be added to the network:
    - A SourceSink element for the grid
    - A Connection from the grid to the specified node

    Args:
        config: Grid configuration data
        period: Time period in hours (unused - for signature compatibility)
        n_periods: Number of periods (unused - for signature compatibility)

    Returns:
        List of element configs to add to network

    """
    elements: list[dict[str, Any]] = []

    # Create SourceSink for the grid
    elements.append({"element_type": "source_sink", "name": config["name"]})

    # Create Connection from grid to node
    # Grid can both import (target->source flow) and export (source->target flow)
    connection_config: dict[str, Any] = {
        "element_type": "connection",
        "name": f"{config['name']}_connection",
        "source": config["name"],
        "target": config["connection"],
    }

    # Add import limit (target->source: grid provides power TO network)
    if "import_limit" in config:
        connection_config["max_power_target_source"] = config["import_limit"]

    # Add export limit (source->target: network provides power TO grid)
    if "export_limit" in config:
        connection_config["max_power_source_target"] = config["export_limit"]

    # Add import pricing (target->source: cost of grid providing power)
    if "import_price" in config:
        connection_config["price_target_source"] = config["import_price"]

    # Add export pricing (source->target: revenue from exporting to grid)
    # Export price should be negative of the cost (revenue = negative cost)
    if "export_price" in config:
        connection_config["price_source_target"] = config["export_price"]

    elements.append(connection_config)

    return elements


def outputs(
    element_name: str,
    model_outputs: Mapping[str, OutputData],
) -> dict[str, dict[str, OutputData]]:
    """Map model outputs to grid-specific output names.

    Args:
        element_name: Name of the grid element
        model_outputs: Outputs from the model SourceSink and Connection

    Returns:
        Nested dict mapping {element_name: {sensor_name: OutputData}}

    """
    grid_outputs: dict[str, OutputData] = {}

    # Map SourceSink power_in to grid_power_import (grid supplying power TO network)
    if SOURCE_SINK_POWER_IN in model_outputs:
        grid_outputs[GRID_POWER_IMPORT] = model_outputs[SOURCE_SINK_POWER_IN]

    # Map SourceSink power_out to grid_power_export (network supplying power TO grid)
    if SOURCE_SINK_POWER_OUT in model_outputs:
        grid_outputs[GRID_POWER_EXPORT] = model_outputs[SOURCE_SINK_POWER_OUT]

    # Map power balance shadow price
    if SOURCE_SINK_POWER_BALANCE in model_outputs:
        grid_outputs[GRID_POWER_BALANCE] = model_outputs[SOURCE_SINK_POWER_BALANCE]

    return {element_name: grid_outputs}
