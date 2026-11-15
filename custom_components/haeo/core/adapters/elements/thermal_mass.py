"""Thermal mass element adapter for model layer integration.

A thermal mass is a store of heat whose level is its temperature. It builds an
unbounded battery that measures heat from the mass's current temperature, a
node at the ambient temperature, and a conduction connection between them that
carries the heat lost to the surroundings. Every temperature limit is the
priced comfort band, so no temperature the surroundings push it to is forbidden.
"""

from collections.abc import Mapping
from typing import Final, Literal

import numpy as np

from custom_components.haeo.core.adapters.output_utils import connection_power, expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    BatteryElementConfig,
)
from custom_components.haeo.core.model.elements.battery import BATTERY_ENERGY_STORED
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.buffer import BufferRole
from custom_components.haeo.core.schema.elements.thermal_mass import (
    CONF_AMBIENT_TEMPERATURE,
    CONF_COMFORT_COST,
    CONF_HEAT_CAPACITY,
    CONF_HEAT_LOSS,
    CONF_MAX_TEMPERATURE,
    CONF_MIN_TEMPERATURE,
    CONF_TEMPERATURE,
    ELEMENT_TYPE,
    SECTION_COMFORT,
    SECTION_STORAGE,
    SECTION_SURROUNDINGS,
    ThermalMassConfigData,
)

type ThermalMassOutputName = Literal[
    "thermal_mass_temperature",
    "thermal_mass_heat_loss",
]

THERMAL_MASS_OUTPUT_NAMES: Final[frozenset[ThermalMassOutputName]] = frozenset(
    (
        THERMAL_MASS_TEMPERATURE := "thermal_mass_temperature",
        THERMAL_MASS_HEAT_LOSS := "thermal_mass_heat_loss",
    )
)

type ThermalMassDeviceName = Literal[ElementType.THERMAL_MASS]

THERMAL_MASS_DEVICE_NAMES: Final[frozenset[ThermalMassDeviceName]] = frozenset(
    (THERMAL_MASS_DEVICE_THERMAL_MASS := ElementType.THERMAL_MASS,),
)


class ThermalMassAdapter:
    """Adapter for thermal mass elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.ALWAYS
    can_source: bool = True
    can_sink: bool = True
    switchboard: bool = False
    device_names: frozenset[ThermalMassDeviceName] = THERMAL_MASS_DEVICE_NAMES
    buffer_roles: frozenset[BufferRole] = frozenset()

    def model_elements(self, config: ThermalMassConfigData) -> list[ModelElementConfig]:
        """Return the store of heat, its surroundings, and the conduction between them."""
        name = config["name"]
        storage = config[SECTION_STORAGE]
        comfort = config[SECTION_COMFORT]
        surroundings = config[SECTION_SURROUNDINGS]
        heat_capacity = storage[CONF_HEAT_CAPACITY]
        temperature = storage[CONF_TEMPERATURE]

        store: BatteryElementConfig = {
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
            "name": name,
            "capacity": None,
            "initial_charge": 0.0,
            "charge_limit_cost": comfort[CONF_COMFORT_COST],
            "level_offset": temperature,
            "energy_per_level": heat_capacity,
        }
        if (min_temperature := comfort.get(CONF_MIN_TEMPERATURE)) is not None:
            store["min_charge"] = (min_temperature - temperature) * heat_capacity
        if (max_temperature := comfort.get(CONF_MAX_TEMPERATURE)) is not None:
            store["max_charge"] = (max_temperature - temperature) * heat_capacity

        return [
            store,
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": f"{name}:surroundings",
                "is_source": True,
                "is_sink": True,
                "level": surroundings[CONF_AMBIENT_TEMPERATURE],
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:heat_loss",
                "source": name,
                "target": f"{name}:surroundings",
                "segments": {
                    "conduction": {"segment_type": "conduction", "conductance": surroundings[CONF_HEAT_LOSS]},
                },
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        *,
        config: ThermalMassConfigData,
        **_kwargs: object,
    ) -> Mapping[ThermalMassDeviceName, Mapping[ThermalMassOutputName, OutputData]]:
        """Map the stored heat to a temperature, and report the heat lost to the surroundings."""
        storage = config[SECTION_STORAGE]
        energy = expect_output_data(model_outputs[name][BATTERY_ENERGY_STORED])
        temperatures = storage[CONF_TEMPERATURE] + np.asarray(energy.values, dtype=float) / storage[CONF_HEAT_CAPACITY]
        heat_loss = connection_power(model_outputs.get(f"{name}:heat_loss"), len(energy.values) - 1)
        return {
            THERMAL_MASS_DEVICE_THERMAL_MASS: {
                THERMAL_MASS_TEMPERATURE: OutputData(
                    type=OutputType.TEMPERATURE, unit="°C", values=tuple(temperatures.tolist())
                ),
                THERMAL_MASS_HEAT_LOSS: OutputData(
                    type=OutputType.POWER, unit="kW", values=heat_loss.values, direction="-"
                ),
            }
        }


adapter = ThermalMassAdapter()
