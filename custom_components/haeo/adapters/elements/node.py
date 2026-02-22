"""Node element adapter for model layer integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal

from homeassistant.components.switch import SwitchEntityDescription

from custom_components.haeo.adapters.output_utils import expect_output_data
from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.model.elements.node import NODE_POWER_BALANCE
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.schema.elements import ElementType
from custom_components.haeo.schema.elements.node import (
    CONF_IS_SINK,
    CONF_IS_SOURCE,
    ELEMENT_TYPE,
    SECTION_ROLE,
    NodeConfigData,
)
from custom_components.haeo.sections import SECTION_COMMON

# Defaults for absent optional fields (no-op values: pure junction behavior)
DEFAULT_IS_SOURCE: Final[bool] = False
DEFAULT_IS_SINK: Final[bool] = False

# Node output names
type NodeOutputName = Literal["node_power_balance"]

NODE_OUTPUT_NAMES: Final[frozenset[NodeOutputName]] = frozenset((NODE_POWER_BALANCE,))

type NodeDeviceName = Literal[ElementType.NODE]

NODE_DEVICE_NAMES: Final[frozenset[NodeDeviceName]] = frozenset(
    (NODE_DEVICE_NODE := ElementType.NODE,),
)


class NodeAdapter:
    """Adapter for Node elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.ALWAYS

    def inputs(self, config: Any) -> dict[str, dict[str, InputFieldInfo[Any]]]:
        """Return input field definitions for node elements."""
        _ = config
        return {
            SECTION_ROLE: {
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
            },
        }

    def model_elements(self, config: NodeConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Node configuration."""
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": config[SECTION_COMMON]["name"],
                "is_source": config[SECTION_ROLE].get(CONF_IS_SOURCE, DEFAULT_IS_SOURCE),
                "is_sink": config[SECTION_ROLE].get(CONF_IS_SINK, DEFAULT_IS_SINK),
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
            node_outputs[NODE_POWER_BALANCE] = expect_output_data(node_model[NODE_POWER_BALANCE])

        return {NODE_DEVICE_NODE: node_outputs}


adapter = NodeAdapter()
