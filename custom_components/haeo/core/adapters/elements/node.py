"""Node element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from typing import Any, Final, Literal, cast

from custom_components.haeo.core.adapters.output_utils import balance_shadow_price_device_outputs, expect_output_data
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
type NodeOutputName = Literal["node_power_balance", "node_tag_power_balance"]

NODE_POWER_BALANCE: Final[NodeOutputName] = "node_power_balance"
NODE_TAG_POWER_BALANCE: Final[NodeOutputName] = "node_tag_power_balance"
NODE_OUTPUT_NAMES: Final[frozenset[NodeOutputName]] = frozenset(
    (NODE_POWER_BALANCE, NODE_TAG_POWER_BALANCE),
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
        *,
        periods: Sequence[float],
        **_kwargs: Any,
    ) -> Mapping[NodeDeviceName, Mapping[NodeOutputName, OutputData]]:
        """Convert model element outputs to node adapter outputs."""
        node_model = model_outputs[name]
        n_periods = len(periods)

        node_outputs: dict[str, OutputData] = {}
        if ELEMENT_POWER_BALANCE in node_model:
            dual = expect_output_data(node_model[ELEMENT_POWER_BALANCE])
            node_outputs.update(
                balance_shadow_price_device_outputs(
                    element_prefix="node",
                    primary_output_name=NODE_POWER_BALANCE,
                    dual=dual,
                    n_periods=n_periods,
                )
            )

        return {NODE_DEVICE_NODE: cast("Mapping[NodeOutputName, OutputData]", node_outputs)}


adapter = NodeAdapter()
