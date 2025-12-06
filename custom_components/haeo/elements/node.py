"""Network node element configuration for HAEO integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal, TypedDict

from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.source_sink import SOURCE_SINK_POWER_BALANCE
from custom_components.haeo.schema.fields import NameFieldData, NameFieldSchema

ELEMENT_TYPE: Final = "node"

# Node-specific output names
NODE_POWER_BALANCE: Final = "node_power_balance"


class NodeConfigSchema(TypedDict):
    """Node element configuration."""

    element_type: Literal["node"]
    name: NameFieldSchema


class NodeConfigData(TypedDict):
    """Node element configuration."""

    element_type: Literal["node"]
    name: NameFieldData


CONFIG_DEFAULTS: dict[str, Any] = {}


def create_model_elements(
    config: NodeConfigData,
    period: float,  # noqa: ARG001
    n_periods: int,  # noqa: ARG001
) -> list[dict[str, Any]]:
    """Create model elements for Node configuration.

    Returns a list with a single SourceSink element configured as a pure junction.
    Nodes are connection points in the network with no generation or consumption.

    Args:
        config: Node configuration data
        period: Time period in hours (unused - for signature compatibility)
        n_periods: Number of periods (unused - for signature compatibility)

    Returns:
        List of element configs to add to network

    """
    return [
        {
            "element_type": "source_sink",
            "name": config["name"],
            "is_source": False,
            "is_sink": False,
        }
    ]


def outputs(
    element_name: str,
    model_outputs: Mapping[str, OutputData],
) -> dict[str, dict[str, OutputData]]:
    """Convert model element outputs to node adapter outputs.

    Maps SourceSink's generic power_balance output to node-specific node_power_balance.

    Args:
        element_name: Name of the node element
        model_outputs: Outputs from the underlying SourceSink model element

    Returns:
        Nested dict mapping {element_name: {sensor_name: OutputData}}

    """
    node_outputs: dict[str, OutputData] = {}

    # Map SourceSink power_balance to node_power_balance
    if SOURCE_SINK_POWER_BALANCE in model_outputs:
        node_outputs[NODE_POWER_BALANCE] = model_outputs[SOURCE_SINK_POWER_BALANCE]

    return {element_name: node_outputs}
