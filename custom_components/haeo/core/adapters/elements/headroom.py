"""Headroom element adapter for model layer integration."""

from collections.abc import Mapping
from typing import Final, Literal

from custom_components.haeo.core.adapters.elements.reserve import requirement_model_element, requirement_outputs
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.headroom import ELEMENT_TYPE, HeadroomConfigData

type HeadroomOutputName = Literal[
    "headroom_energy_required",
    "headroom_energy_available",
    "headroom_energy_shortfall",
    "headroom_state_of_charge",
]

HEADROOM_OUTPUT_NAMES: Final[frozenset[HeadroomOutputName]] = frozenset(
    (
        HEADROOM_ENERGY_REQUIRED := "headroom_energy_required",
        HEADROOM_ENERGY_AVAILABLE := "headroom_energy_available",
        HEADROOM_ENERGY_SHORTFALL := "headroom_energy_shortfall",
        HEADROOM_STATE_OF_CHARGE := "headroom_state_of_charge",
    )
)

type HeadroomDeviceName = Literal[ElementType.HEADROOM]

HEADROOM_DEVICE_NAMES: Final[frozenset[HeadroomDeviceName]] = frozenset(
    (HEADROOM_DEVICE_HEADROOM := ElementType.HEADROOM,)
)


class HeadroomAdapter:
    """Adapter for Headroom elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER
    can_source: bool = False
    can_sink: bool = False

    def model_elements(self, config: HeadroomConfigData) -> list[ModelElementConfig]:
        """Create the headroom model element."""
        return requirement_model_element(config, "headroom")

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: object,
    ) -> Mapping[HeadroomDeviceName, Mapping[HeadroomOutputName, OutputData]]:
        """Map model outputs to headroom output names."""
        required, available, shortfall, state_of_charge = requirement_outputs(name, model_outputs)
        return {
            HEADROOM_DEVICE_HEADROOM: {
                HEADROOM_ENERGY_REQUIRED: required,
                HEADROOM_ENERGY_AVAILABLE: available,
                HEADROOM_ENERGY_SHORTFALL: shortfall,
                HEADROOM_STATE_OF_CHARGE: state_of_charge,
            }
        }


adapter = HeadroomAdapter()
