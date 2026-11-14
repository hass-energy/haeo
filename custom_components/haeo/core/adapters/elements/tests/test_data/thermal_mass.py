"""Adapter mapping cases for the thermal mass element."""

import numpy as np

from custom_components.haeo.core.adapters.elements.thermal_mass import (
    THERMAL_MASS_DEVICE_THERMAL_MASS,
    THERMAL_MASS_HEAT_LOSS,
    THERMAL_MASS_TEMPERATURE,
)
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    battery,
    connection,
)
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.thermal_mass import ThermalMassConfigData

from . import CreateCase, OutputsCase

CREATE_CASES: list[CreateCase] = [
    {
        "description": "Thermal mass stores heat above the lowest temperature it can reach",
        "data": ThermalMassConfigData(
            element_type=ElementType.THERMAL_MASS,
            name="tank",
            storage={
                "heat_capacity": 0.2,
                "temperature": 50.0,
                "lowest_temperature": 10.0,
                "highest_temperature": 70.0,
            },
            comfort={
                "min_temperature": np.array([40.0, 40.0, 40.0]),
                "max_temperature": np.array([65.0, 65.0, 65.0]),
                "comfort_cost": 1.0,
            },
            surroundings={"ambient_temperature": np.array([20.0, 20.0]), "heat_loss": 0.002},
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "tank",
                "capacity": 12.0,
                "initial_charge": 8.0,
                "charge_limit_cost": 1.0,
                "level_offset": 10.0,
                "energy_per_level": 0.2,
                "min_charge": [6.0, 6.0, 6.0],
                "max_charge": [11.0, 11.0, 11.0],
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": "tank:surroundings",
                "is_source": True,
                "is_sink": True,
                "level": [20.0, 20.0],
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "tank:heat_loss",
                "source": "tank",
                "target": "tank:surroundings",
                "segments": {"conduction": {"segment_type": "conduction", "conductance": 0.002}},
            },
        ],
    },
    {
        "description": "Thermal mass without limits or a comfort band spans only its own and the ambient temperatures",
        "data": ThermalMassConfigData(
            element_type=ElementType.THERMAL_MASS,
            name="room",
            storage={"heat_capacity": 1.0, "temperature": 21.0},
            comfort={"comfort_cost": 0.5},
            surroundings={"ambient_temperature": np.array([10.0, 30.0]), "heat_loss": 0.1},
        ),
        "model": [
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": "room",
                "capacity": 20.0,
                "initial_charge": 11.0,
                "charge_limit_cost": 0.5,
                "level_offset": 10.0,
                "energy_per_level": 1.0,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": "room:surroundings",
                "is_source": True,
                "is_sink": True,
                "level": [10.0, 30.0],
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "room:heat_loss",
                "source": "room",
                "target": "room:surroundings",
                "segments": {"conduction": {"segment_type": "conduction", "conductance": 0.1}},
            },
        ],
    },
]


OUTPUTS_CASES: list[OutputsCase] = [
    {
        "description": "Thermal mass reports its temperature and the heat it loses",
        "data": ThermalMassConfigData(
            element_type=ElementType.THERMAL_MASS,
            name="room",
            storage={"heat_capacity": 2.0, "temperature": 21.0},
            comfort={"comfort_cost": 0.5},
            surroundings={"ambient_temperature": np.array([15.0]), "heat_loss": 0.1},
        ),
        "model_outputs": {
            "room": {
                battery.BATTERY_ENERGY_STORED: OutputData(type=OutputType.ENERGY, unit="kWh", values=(12.0, 11.0)),
            },
            "room:heat_loss": {
                connection.CONNECTION_POWER: OutputData(
                    type=OutputType.POWER_FLOW, unit="kW", values=(1.0,), direction="+"
                ),
            },
        },
        "periods": np.array([1.0]),
        "outputs": {
            THERMAL_MASS_DEVICE_THERMAL_MASS: {
                THERMAL_MASS_TEMPERATURE: OutputData(type=OutputType.TEMPERATURE, unit="°C", values=(21.0, 20.5)),
                THERMAL_MASS_HEAT_LOSS: OutputData(type=OutputType.POWER, unit="kW", values=(1.0,), direction="-"),
            }
        },
    },
]
