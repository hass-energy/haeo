"""Network node element configuration for HAEO integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.node import NODE_POWER_BALANCE
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.schema.fields import BooleanFieldData, BooleanFieldSchema, NameFieldData, NameFieldSchema

ELEMENT_TYPE: Final = "node"

# Configuration field names
CONF_IS_SOURCE: Final = "is_source"
CONF_IS_SINK: Final = "is_sink"

type NodeOutputName = Literal["node_power_balance"]

NODE_OUTPUT_NAMES: Final[frozenset[NodeOutputName]] = frozenset((NODE_POWER_BALANCE,))

type NodeDeviceName = Literal["node"]

NODE_DEVICE_NAMES: Final[frozenset[NodeDeviceName]] = frozenset(
    (NODE_DEVICE_NODE := ELEMENT_TYPE,),
)


class NodeConfigSchema(TypedDict):
    """Node element configuration.

    In standard mode, nodes are pure junctions (is_source=False, is_sink=False).
    In advanced mode, is_source and is_sink can be configured to create:
    - Grid-like nodes (is_source=True, is_sink=True): Can import and export power
    - Load-like nodes (is_source=False, is_sink=True): Can only consume power
    - Source-like nodes (is_source=True, is_sink=False): Can only produce power
    - Pure junctions (is_source=False, is_sink=False): Power must balance
    """

    element_type: Literal["node"]
    name: NameFieldSchema

    is_source: BooleanFieldSchema
    is_sink: BooleanFieldSchema


class NodeConfigData(TypedDict):
    """Node element configuration."""

    element_type: Literal["node"]
    name: NameFieldData

    is_source: BooleanFieldData
    is_sink: BooleanFieldData


CONFIG_DEFAULTS: dict[str, Any] = {
    CONF_IS_SOURCE: False,
    CONF_IS_SINK: False,
}


def create_model_elements(config: NodeConfigData) -> list[dict[str, Any]]:
    """Create model elements for Node configuration."""
    return [
        {
            "element_type": "node",
            "name": config["name"],
            "is_source": config["is_source"],
            "is_sink": config["is_sink"],
        }
    ]


def outputs(
    name: str, outputs: Mapping[str, Mapping[ModelOutputName, OutputData]], _config: NodeConfigData
) -> Mapping[NodeDeviceName, Mapping[NodeOutputName, OutputData]]:
    """Convert model element outputs to node adapter outputs."""

    node_model = outputs[name]

    # Map Node power_balance to node_power_balance (only present for constrained nodes)
    node_outputs: dict[NodeOutputName, OutputData] = {}
    if NODE_POWER_BALANCE in node_model:
        node_outputs[NODE_POWER_BALANCE] = node_model[NODE_POWER_BALANCE]

    return {NODE_DEVICE_NODE: node_outputs}
