"""Junction element adapter for model layer integration."""

from collections.abc import Mapping
from typing import Final, Literal

from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.junction import ELEMENT_TYPE, JunctionConfigData

type JunctionOutputName = Literal["junction_power_balance"]

JUNCTION_POWER_BALANCE: Final[JunctionOutputName] = "junction_power_balance"
JUNCTION_OUTPUT_NAMES: Final[frozenset[JunctionOutputName]] = frozenset((JUNCTION_POWER_BALANCE,))

type JunctionDeviceName = Literal[ElementType.JUNCTION]

JUNCTION_DEVICE_NAMES: Final[frozenset[JunctionDeviceName]] = frozenset(
    (JUNCTION_DEVICE_JUNCTION := ElementType.JUNCTION,),
)


class JunctionAdapter:
    """Adapter for Junction elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.ALWAYS
    can_source: bool = False
    can_sink: bool = False

    def model_elements(self, config: JunctionConfigData) -> list[ModelElementConfig]:
        """Return a model node that neither produces nor consumes power."""
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": config["name"],
                "is_source": False,
                "is_sink": False,
            }
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: object,
    ) -> Mapping[JunctionDeviceName, Mapping[JunctionOutputName, OutputData]]:
        """Convert model element outputs to junction adapter outputs."""
        junction_model = model_outputs[name]
        junction_outputs: dict[JunctionOutputName, OutputData] = {}
        if ELEMENT_POWER_BALANCE in junction_model:
            junction_outputs[JUNCTION_POWER_BALANCE] = expect_output_data(junction_model[ELEMENT_POWER_BALANCE])
        return {JUNCTION_DEVICE_JUNCTION: junction_outputs}


adapter = JunctionAdapter()
