"""Reserve element adapter for model layer integration.

Also holds the helpers headroom shares, since a headroom is a reserve of empty
space rather than of energy.
"""

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
    StorageRequirementData,
)

type ReserveOutputName = Literal[
    "reserve_energy_required",
    "reserve_energy_available",
    "reserve_energy_shortfall",
    "reserve_state_of_charge",
]

RESERVE_OUTPUT_NAMES: Final[frozenset[ReserveOutputName]] = frozenset(
    (
        RESERVE_ENERGY_REQUIRED := "reserve_energy_required",
        RESERVE_ENERGY_AVAILABLE := "reserve_energy_available",
        RESERVE_ENERGY_SHORTFALL := "reserve_energy_shortfall",
        RESERVE_STATE_OF_CHARGE := "reserve_state_of_charge",
    )
)

type ReserveDeviceName = Literal[ElementType.RESERVE]

RESERVE_DEVICE_NAMES: Final[frozenset[ReserveDeviceName]] = frozenset((RESERVE_DEVICE_RESERVE := ElementType.RESERVE,))


def requirement_model_element(
    config: StorageRequirementData, kind: model_reserve.ReserveKind
) -> list[ModelElementConfig]:
    """Create the requirement's model element over its loads, generation, and storage.

    Loads and generation offset each other: generation lowers a reserve and
    loads lower a headroom.
    """
    participants = config[SECTION_PARTICIPANTS]
    requirement = config[SECTION_REQUIREMENT]
    return [
        {
            "element_type": MODEL_ELEMENT_TYPE_RESERVE,
            "name": config["name"],
            "kind": kind,
            "loads": list(participants.get(CONF_LOADS, [])),
            "generation": list(participants.get(CONF_GENERATION, [])),
            "storage": list(participants[CONF_STORAGE]),
            "window": requirement[CONF_WINDOW],
            "minimum": requirement[CONF_MINIMUM],
            "price": config[SECTION_PRICING][CONF_SHORTFALL_COST],
        }
    ]


def requirement_outputs(
    name: str, model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]
) -> tuple[OutputData, OutputData, OutputData, OutputData]:
    """Return the required, available, and shortfall energy and the state of charge line."""
    outputs = model_outputs[name]
    return (
        expect_output_data(outputs[model_reserve.RESERVE_ENERGY_REQUIRED]),
        expect_output_data(outputs[model_reserve.RESERVE_ENERGY_AVAILABLE]),
        expect_output_data(outputs[model_reserve.RESERVE_ENERGY_SHORTFALL]),
        expect_output_data(outputs[model_reserve.RESERVE_STATE_OF_CHARGE]),
    )


class ReserveAdapter:
    """Adapter for Reserve elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER
    can_source: bool = False
    can_sink: bool = False

    def model_elements(self, config: ReserveConfigData) -> list[ModelElementConfig]:
        """Create the reserve model element."""
        return requirement_model_element(config, "reserve")

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: object,
    ) -> Mapping[ReserveDeviceName, Mapping[ReserveOutputName, OutputData]]:
        """Map model outputs to reserve output names."""
        required, available, shortfall, state_of_charge = requirement_outputs(name, model_outputs)
        return {
            RESERVE_DEVICE_RESERVE: {
                RESERVE_ENERGY_REQUIRED: required,
                RESERVE_ENERGY_AVAILABLE: available,
                RESERVE_ENERGY_SHORTFALL: shortfall,
                RESERVE_STATE_OF_CHARGE: state_of_charge,
            }
        }


adapter = ReserveAdapter()
