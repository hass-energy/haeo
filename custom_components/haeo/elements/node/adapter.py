"""Node element adapter for model layer integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal

from homeassistant.components.switch import SwitchEntityDescription

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.model.elements.node import NODE_POWER_BALANCE
from custom_components.haeo.model.output_data import OutputData

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
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.ALWAYS

    def available(self, config: NodeConfigSchema, **_kwargs: Any) -> bool:
        """Check if node configuration can be loaded."""
        # Nodes only have constant fields, always available
        _ = config  # Unused but required by protocol
        return True

    def inputs(self, config: Any) -> dict[str, InputFieldInfo[Any]]:
        """Return input field definitions for node elements."""
        _ = config
        return {
            CONF_IS_SOURCE: InputFieldInfo(
                field_name=CONF_IS_SOURCE,
                entity_description=SwitchEntityDescription(
                    key=CONF_IS_SOURCE,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_IS_SOURCE}",
                ),
                output_type=OutputType.STATUS,
                defaults=InputFieldDefaults(mode="value", value=False),
            ),
            CONF_IS_SINK: InputFieldInfo(
                field_name=CONF_IS_SINK,
                entity_description=SwitchEntityDescription(
                    key=CONF_IS_SINK,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_IS_SINK}",
                ),
                output_type=OutputType.STATUS,
                defaults=InputFieldDefaults(mode="value", value=False),
            ),
        }

    def build_config_data(
        self,
        loaded_values: NodeConfigData,
        config: NodeConfigSchema,
    ) -> NodeConfigData:
        """Build ConfigData from pre-loaded values.

        This is the single source of truth for ConfigData construction.
        The coordinator uses this method after loading input entity values.

        Args:
            loaded_values: Dict of field names to loaded values (from input entities)
            config: Original ConfigSchema for non-input fields (element_type, name)

        Returns:
            NodeConfigData with loaded values (defaults applied in model_elements)

        """
        data: NodeConfigData = {
            "element_type": config["element_type"],
            "name": config["name"],
        }
        if CONF_IS_SOURCE in loaded_values:
            data["is_source"] = loaded_values[CONF_IS_SOURCE]
        if CONF_IS_SINK in loaded_values:
            data["is_sink"] = loaded_values[CONF_IS_SINK]
        return data

    def model_elements(self, config: NodeConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Node configuration."""
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": config["name"],
                "is_source": config.get(CONF_IS_SOURCE, DEFAULT_IS_SOURCE),
                "is_sink": config.get(CONF_IS_SINK, DEFAULT_IS_SINK),
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
            power_balance = node_model[NODE_POWER_BALANCE]
            if not isinstance(power_balance, OutputData):
                msg = f"Expected OutputData for {name!r} {NODE_POWER_BALANCE}"
                raise TypeError(msg)
            node_outputs[NODE_POWER_BALANCE] = power_balance

        return {NODE_DEVICE_NODE: node_outputs}


adapter = NodeAdapter()
