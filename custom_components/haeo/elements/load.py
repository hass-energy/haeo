"""Load element configuration for HAEO integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal, TypedDict

from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.source_sink import SOURCE_SINK_POWER_BALANCE, SOURCE_SINK_POWER_IN
from custom_components.haeo.schema.fields import (
    ElementNameFieldSchema,
    NameFieldData,
    NameFieldSchema,
    PowerSensorsFieldData,
    PowerSensorsFieldSchema,
)

ELEMENT_TYPE: Final = "load"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_CONNECTION: Final = "connection"

# Load-specific sensor names (for translation/output mapping)
LOAD_POWER_CONSUMED: Final = "load_power_consumed"
LOAD_POWER_BALANCE: Final = "load_power_balance"


class LoadConfigSchema(TypedDict):
    """Load element configuration."""

    element_type: Literal["load"]
    name: NameFieldSchema
    connection: ElementNameFieldSchema  # Connection ID that load connects to
    forecast: PowerSensorsFieldSchema


class LoadConfigData(TypedDict):
    """Load element configuration."""

    element_type: Literal["load"]
    name: NameFieldData
    connection: ElementNameFieldSchema  # Connection ID that load connects to
    forecast: PowerSensorsFieldData


CONFIG_DEFAULTS: dict[str, Any] = {}


def create_model_elements(
    config: LoadConfigData,
    period: float,  # noqa: ARG001
    n_periods: int,  # noqa: ARG001
) -> list[dict[str, Any]]:
    """Create model elements for Load configuration.

    Returns a list of element configurations that should be added to the network:
    - A SourceSink element for the load
    - A Connection to the load from the specified node

    Args:
        config: Load configuration data
        period: Time period in hours (unused - for signature compatibility)
        n_periods: Number of periods (unused - for signature compatibility)

    Returns:
        List of element configs to add to network

    """
    elements: list[dict[str, Any]] = []

    # Create SourceSink for the load
    elements.append({"element_type": "source_sink", "name": config["name"]})

    # Create Connection from node to load
    # Load only consumes power (source->target flow: network TO load)
    connection_config: dict[str, Any] = {
        "element_type": "connection",
        "name": f"{config['name']}_connection",
        "source": config["connection"],
        "target": config["name"],
    }

    # Add forecast as power limit (source->target: maximum load consumption)
    connection_config["max_power_source_target"] = config["forecast"]

    elements.append(connection_config)

    return elements


def outputs(
    element_name: str,
    model_outputs: Mapping[str, OutputData],
) -> dict[str, dict[str, OutputData]]:
    """Map model outputs to load-specific output names.

    Args:
        element_name: Name of the load element
        model_outputs: Outputs from the model SourceSink and Connection

    Returns:
        Nested dict mapping {element_name: {sensor_name: OutputData}}

    """
    load_outputs: dict[str, OutputData] = {}

    # Map SourceSink power_in to load_power_consumed (load consuming power FROM network)
    if SOURCE_SINK_POWER_IN in model_outputs:
        load_outputs[LOAD_POWER_CONSUMED] = model_outputs[SOURCE_SINK_POWER_IN]

    # Map power balance shadow price
    if SOURCE_SINK_POWER_BALANCE in model_outputs:
        load_outputs[LOAD_POWER_BALANCE] = model_outputs[SOURCE_SINK_POWER_BALANCE]

    return {element_name: load_outputs}
