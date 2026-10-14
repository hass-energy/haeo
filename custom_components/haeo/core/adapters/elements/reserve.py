"""Reserve element adapter for model layer integration.

Also holds the helpers headroom shares, since a headroom is a reserve of empty
space rather than of energy.
"""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

import numpy as np

from custom_components.haeo.core.adapters.elements.battery import battery_ceiling_ratio, battery_floor_ratio
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
    CONF_EFFICIENCY_TARGET_SOURCE,
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
    name: str,
    model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
    config: StorageRequirementData,
    participants: Mapping[str, ElementConfigData],
    kind: model_reserve.ReserveKind,
) -> tuple[OutputData, OutputData, OutputData, OutputData]:
    """Return the required, available, and shortfall energy and the state of charge line."""
    outputs = model_outputs[name]
    required = expect_output_data(outputs[model_reserve.RESERVE_ENERGY_REQUIRED])
    batteries = [
        battery
        for battery_name in config[SECTION_PARTICIPANTS][CONF_STORAGE]
        if is_battery_config_data(battery := participants[battery_name])
    ]
    return (
        required,
        expect_output_data(outputs[model_reserve.RESERVE_ENERGY_AVAILABLE]),
        expect_output_data(outputs[model_reserve.RESERVE_ENERGY_SHORTFALL]),
        _state_of_charge(required, batteries, kind),
    )


def _state_of_charge(
    required: OutputData, batteries: Sequence[BatteryConfigData], kind: model_reserve.ReserveKind
) -> OutputData:
    """Return the combined state of charge line for the requirement.

    For a reserve, the batteries should stay above their floors plus the reserve
    stored at their discharge efficiency. For headroom, they should stay below
    their ceilings less the space the headroom takes up at their charge
    efficiency. Efficiencies are weighted by capacity, so the line is exact for
    a single battery and for batteries with the same efficiency.
    """
    n_boundaries = len(required.values)
    efficiency_field = CONF_EFFICIENCY_SOURCE_TARGET if kind == "reserve" else CONF_EFFICIENCY_TARGET_SOURCE
    capacity = np.zeros(n_boundaries)
    limit_energy = np.zeros(n_boundaries)
    weighted_efficiency = np.zeros(n_boundaries)
    for battery in batteries:
        battery_capacity = np.asarray(battery[BATTERY_SECTION_STORAGE][CONF_CAPACITY], dtype=float)
        efficiency = broadcast_to_sequence(battery[SECTION_EFFICIENCY].get(efficiency_field, 1.0), n_boundaries)
        limit_ratio = battery_floor_ratio(battery) if kind == "reserve" else battery_ceiling_ratio(battery)
        capacity += battery_capacity
        limit_energy += limit_ratio * battery_capacity
        weighted_efficiency += efficiency * battery_capacity
    required_energy = np.asarray(required.values, dtype=float)
    if kind == "reserve":
        ratio = np.minimum((limit_energy + required_energy * capacity / weighted_efficiency) / capacity, 1.0)
    else:
        ratio = np.maximum((limit_energy - required_energy * weighted_efficiency / capacity) / capacity, 0.0)
    return OutputData(type=OutputType.STATE_OF_CHARGE, unit="%", values=tuple(ratio.tolist()))


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
        *,
        config: ReserveConfigData,
        participants: Mapping[str, ElementConfigData],
        **_kwargs: object,
    ) -> Mapping[ReserveDeviceName, Mapping[ReserveOutputName, OutputData]]:
        """Map model outputs to reserve output names."""
        required, available, shortfall, state_of_charge = requirement_outputs(
            name, model_outputs, config, participants, "reserve"
        )
        return {
            RESERVE_DEVICE_RESERVE: {
                RESERVE_ENERGY_REQUIRED: required,
                RESERVE_ENERGY_AVAILABLE: available,
                RESERVE_ENERGY_SHORTFALL: shortfall,
                RESERVE_STATE_OF_CHARGE: state_of_charge,
            }
        }


adapter = ReserveAdapter()
