"""Network node element configuration for HAEO integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal, TypedDict

from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.source_sink import SOURCE_SINK_POWER_BALANCE
from custom_components.haeo.schema.fields import NameFieldData, NameFieldSchema

ELEMENT_TYPE: Final = "node"

type NodeOutputName = Literal["node_power_balance"]

NODE_OUTPUT_NAMES: Final[frozenset[NodeOutputName]] = frozenset(
    (NODE_POWER_BALANCE := "node_power_balance",),
)

type NodeDeviceName = Literal["node"]

NODE_DEVICE_NAMES: Final[frozenset[NodeDeviceName]] = frozenset(
    (NODE_DEVICE_NODE := ELEMENT_TYPE,),
)


class NodeConfigSchema(TypedDict):
    """Node element configuration."""

    element_type: Literal["node"]
    name: NameFieldSchema


class NodeConfigData(TypedDict):
    """Node element configuration."""

    element_type: Literal["node"]
    name: NameFieldData


CONFIG_DEFAULTS: dict[str, Any] = {}


def create_model_elements(config: NodeConfigData) -> list[dict[str, Any]]:
    """Create model elements for Node configuration."""
    # Node is a pure junction - no power generation or consumption
    return [{"element_type": "source_sink", "name": config["name"], "is_source": False, "is_sink": False}]


def outputs(
    name: str, outputs: Mapping[str, Mapping[ModelOutputName, OutputData]], _config: NodeConfigData
) -> Mapping[NodeDeviceName, Mapping[NodeOutputName, OutputData]]:
    """Provide state updates for node output sensors."""
    source_sink = outputs[name]

    # Map SourceSink power_balance to node_power_balance
    node_outputs: dict[NodeOutputName, OutputData] = {
        NODE_POWER_BALANCE: source_sink[SOURCE_SINK_POWER_BALANCE],
    }

    return {NODE_DEVICE_NODE: node_outputs}
