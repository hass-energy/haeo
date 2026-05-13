"""Node element adapter for model layer integration."""

from collections.abc import Mapping
from typing import Any, Final, Literal

from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.node import (
    CONF_IS_SINK,
    CONF_IS_SOURCE,
    ELEMENT_TYPE,
    SECTION_ROLE,
    NodeConfigData,
)

# Defaults for absent optional fields (no-op values: pure junction behavior)
DEFAULT_IS_SOURCE: Final[bool] = False
DEFAULT_IS_SINK: Final[bool] = False

# Node output names
type NodeOutputName = Literal["node_power_balance_shadow_energy_price"]

NODE_OUTPUT_NAMES: Final[frozenset[NodeOutputName]] = frozenset(
    (NODE_POWER_BALANCE_SHADOW_ENERGY_PRICE := "node_power_balance_shadow_energy_price",)
)

type NodeDeviceName = Literal[ElementType.NODE]

NODE_DEVICE_NAMES: Final[frozenset[NodeDeviceName]] = frozenset(
    (NODE_DEVICE_NODE := ElementType.NODE,),
)


class NodeAdapter:
    """Adapter for Node elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.ALWAYS
    can_source: bool = True
    can_sink: bool = True

    def model_elements(self, config: NodeConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Node configuration."""
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": config["name"],
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

        # power_balance is formulated in energy units (kWh) at the LP layer,
        # so its shadow price is already $/kWh and can be published directly.
        node_outputs: dict[NodeOutputName, OutputData] = {}
        if ELEMENT_POWER_BALANCE in node_model:
            node_outputs[NODE_POWER_BALANCE_SHADOW_ENERGY_PRICE] = expect_output_data(node_model[ELEMENT_POWER_BALANCE])

        return {NODE_DEVICE_NODE: node_outputs}


adapter = NodeAdapter()
