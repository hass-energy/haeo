"""Reserve element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

import numpy as np

from custom_components.haeo.core.adapters.elements.battery import battery_floor_ratio
from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_RESERVE
from custom_components.haeo.core.model.elements import reserve as model_reserve
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.util import broadcast_to_sequence
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_EFFICIENCY_SOURCE_TARGET,
    SECTION_EFFICIENCY,
    BatteryConfigData,
    is_battery_config_data,
)
from custom_components.haeo.core.schema.elements.battery import SECTION_STORAGE as BATTERY_SECTION_STORAGE
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
        *,
        config: ReserveConfigData,
        participants: Mapping[str, ElementConfigData],
        **_kwargs: object,
    ) -> Mapping[ReserveDeviceName, Mapping[ReserveOutputName, OutputData]]:
        """Map model outputs to reserve output names."""
        reserve_outputs = model_outputs[name]
        required = expect_output_data(reserve_outputs[model_reserve.RESERVE_ENERGY_REQUIRED])
        batteries = [
            battery
            for battery_name in config[SECTION_PARTICIPANTS][CONF_STORAGE]
            if is_battery_config_data(battery := participants[battery_name])
        ]
        return {
            RESERVE_DEVICE_RESERVE: {
                RESERVE_ENERGY_REQUIRED: required,
                RESERVE_ENERGY_AVAILABLE: expect_output_data(reserve_outputs[model_reserve.RESERVE_ENERGY_AVAILABLE]),
                RESERVE_ENERGY_SHORTFALL: expect_output_data(reserve_outputs[model_reserve.RESERVE_ENERGY_SHORTFALL]),
                RESERVE_STATE_OF_CHARGE: _state_of_charge(required, batteries),
            }
        }


def _state_of_charge(required: OutputData, batteries: Sequence[BatteryConfigData]) -> OutputData:
    """Return the combined state of charge the batteries should stay above to hold the reserve.

    The batteries' floors stay below the reserve, and the reserve itself is stored
    at their capacity-weighted discharge efficiency, so the line is exact for a
    single battery and for batteries with the same efficiency.
    """
    n_boundaries = len(required.values)
    capacity = np.zeros(n_boundaries)
    floor_energy = np.zeros(n_boundaries)
    deliverable_capacity = np.zeros(n_boundaries)
    for battery in batteries:
        battery_capacity = np.asarray(battery[BATTERY_SECTION_STORAGE][CONF_CAPACITY], dtype=float)
        efficiency = broadcast_to_sequence(
            battery[SECTION_EFFICIENCY].get(CONF_EFFICIENCY_SOURCE_TARGET, 1.0), n_boundaries
        )
        capacity += battery_capacity
        floor_energy += battery_floor_ratio(battery) * battery_capacity
        deliverable_capacity += efficiency * battery_capacity
    stored = np.asarray(required.values, dtype=float) * capacity / deliverable_capacity
    ratio = np.minimum((floor_energy + stored) / capacity, 1.0)
    return OutputData(type=OutputType.STATE_OF_CHARGE, unit="%", values=tuple(ratio.tolist()))


adapter = ReserveAdapter()
