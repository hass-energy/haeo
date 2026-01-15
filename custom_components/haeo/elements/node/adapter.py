"""Node element adapter for model layer integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import ConstantLoader
from custom_components.haeo.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.model.elements.node import NODE_POWER_BALANCE
from custom_components.haeo.model.output_data import OutputData

from .flow import NodeSubentryFlowHandler
from .schema import CONF_IS_SINK, CONF_IS_SOURCE, ELEMENT_TYPE, NodeConfigData, NodeConfigSchema

# Defaults for absent optional fields (no-op values: pure junction behavior)
DEFAULT_IS_SOURCE: Final[bool] = False
DEFAULT_IS_SINK: Final[bool] = False

# Node output names
type NodeOutputName = Literal["node_power_balance"]

NODE_OUTPUT_NAMES: Final[frozenset[NodeOutputName]] = frozenset((NODE_POWER_BALANCE,))

type NodeDeviceName = Literal["node"]

NODE_DEVICE_NAMES: Final[frozenset[NodeDeviceName]] = frozenset(
    (NODE_DEVICE_NODE := "node",),
)


class NodeAdapter:
    """Adapter for Node elements."""

    element_type: str = ELEMENT_TYPE
    flow_class: type = NodeSubentryFlowHandler
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.ALWAYS

    def available(self, config: NodeConfigSchema, **_kwargs: Any) -> bool:
        """Check if node configuration can be loaded."""
        # Nodes only have constant fields, always available
        _ = config  # Unused but required by protocol
        return True

    def build_config_data(
        self,
        loaded_values: Mapping[str, Any],
        config: NodeConfigSchema,
    ) -> NodeConfigData:
        """Build ConfigData from pre-loaded values.

        This is the single source of truth for ConfigData construction.
        Both load() and the coordinator use this method.

        Args:
            loaded_values: Dict of field names to loaded values (from input entities or ConstantLoader)
            config: Original ConfigSchema for non-input fields (element_type, name)

        Returns:
            NodeConfigData with all fields populated and defaults applied

        """
        return {
            "element_type": config["element_type"],
            "name": config["name"],
            "is_source": bool(loaded_values.get(CONF_IS_SOURCE, DEFAULT_IS_SOURCE)),
            "is_sink": bool(loaded_values.get(CONF_IS_SINK, DEFAULT_IS_SINK)),
        }

    async def load(self, config: NodeConfigSchema, **_kwargs: Any) -> NodeConfigData:
        """Load node configuration values.

        Uses ConstantLoader for boolean fields, then delegates to build_config_data().
        """
        const_loader_bool = ConstantLoader[bool](bool)
        loaded_values: dict[str, bool] = {}

        # Load boolean fields with defaults
        if CONF_IS_SOURCE in config:
            loaded_values[CONF_IS_SOURCE] = await const_loader_bool.load(value=config[CONF_IS_SOURCE])
        if CONF_IS_SINK in config:
            loaded_values[CONF_IS_SINK] = await const_loader_bool.load(value=config[CONF_IS_SINK])

        return self.build_config_data(loaded_values, config)

    def model_elements(self, config: NodeConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Node configuration."""
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": config["name"],
                "is_source": config["is_source"],
                "is_sink": config["is_sink"],
            }
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[NodeDeviceName, Mapping[NodeOutputName, OutputData]]:
        """Convert model element outputs to node adapter outputs."""
        node_model = model_outputs[name]

        # Map Node power_balance to node_power_balance (only present for constrained nodes)
        node_outputs: dict[NodeOutputName, OutputData] = {}
        if NODE_POWER_BALANCE in node_model:
            node_outputs[NODE_POWER_BALANCE] = node_model[NODE_POWER_BALANCE]

        return {NODE_DEVICE_NODE: node_outputs}


adapter = NodeAdapter()
