"""Reserve element adapter for model layer integration."""

from collections.abc import Mapping
from typing import Final, Literal

from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_RESERVE
from custom_components.haeo.core.model.elements import reserve as model_reserve
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.reserve import (
    CONF_GENERATION,
    CONF_LOADS,
    CONF_MINIMUM,
    CONF_SHORTFALL_COST,
    CONF_STORAGE,
    CONF_WINDOW,
    ELEMENT_TYPE,
    SECTION_PARTICIPANTS,
    SECTION_PRICING,
    SECTION_REQUIREMENT,
    ReserveConfigData,
)

type ReserveOutputName = Literal[
    "reserve_energy_required",
    "reserve_energy_available",
    "reserve_energy_shortfall",
]

RESERVE_OUTPUT_NAMES: Final[frozenset[ReserveOutputName]] = frozenset(
    (
        RESERVE_ENERGY_REQUIRED := "reserve_energy_required",
        RESERVE_ENERGY_AVAILABLE := "reserve_energy_available",
        RESERVE_ENERGY_SHORTFALL := "reserve_energy_shortfall",
    )
)

type ReserveDeviceName = Literal[ElementType.RESERVE]

RESERVE_DEVICE_NAMES: Final[frozenset[ReserveDeviceName]] = frozenset((RESERVE_DEVICE_RESERVE := ElementType.RESERVE,))


class ReserveAdapter:
    """Adapter for Reserve elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER
    can_source: bool = False
    can_sink: bool = False

    def model_elements(self, config: ReserveConfigData) -> list[ModelElementConfig]:
        """Create the reserve model element over the configured loads, generation, and storage.

        Loads and generation both count by the net power flowing into them,
        so generation lowers the reserve by what it supplies.
        """
        participants = config[SECTION_PARTICIPANTS]
        requirement = config[SECTION_REQUIREMENT]
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_RESERVE,
                "name": config["name"],
                "elements": [*participants.get(CONF_LOADS, []), *participants.get(CONF_GENERATION, [])],
                "storage": list(participants[CONF_STORAGE]),
                "window": requirement[CONF_WINDOW],
                "minimum": requirement[CONF_MINIMUM],
                "price": config[SECTION_PRICING][CONF_SHORTFALL_COST],
            }
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: object,
    ) -> Mapping[ReserveDeviceName, Mapping[ReserveOutputName, OutputData]]:
        """Map model outputs to reserve output names."""
        reserve_outputs = model_outputs[name]
        return {
            RESERVE_DEVICE_RESERVE: {
                RESERVE_ENERGY_REQUIRED: expect_output_data(reserve_outputs[model_reserve.RESERVE_ENERGY_REQUIRED]),
                RESERVE_ENERGY_AVAILABLE: expect_output_data(reserve_outputs[model_reserve.RESERVE_ENERGY_AVAILABLE]),
                RESERVE_ENERGY_SHORTFALL: expect_output_data(reserve_outputs[model_reserve.RESERVE_ENERGY_SHORTFALL]),
            }
        }


adapter = ReserveAdapter()
