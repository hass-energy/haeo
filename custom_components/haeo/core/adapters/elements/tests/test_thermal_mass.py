"""Tests for the plans thermal masses get in the optimization."""

from typing import Final

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.adapters.network_builder import build_network
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import Battery, Connection
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.core.schema.elements.connection import ConnectionConfigData
from custom_components.haeo.core.schema.elements.grid import GridConfigData
from custom_components.haeo.core.schema.elements.junction import JunctionConfigData
from custom_components.haeo.core.schema.elements.load import LoadConfigData
from custom_components.haeo.core.schema.elements.thermal_mass import ThermalMassConfigData

HOURS: Final = np.arange(24)
# Cheap overnight, dear from 4 pm to 9 pm
PRICE: Final = np.where(HOURS < 6, 0.10, np.where((HOURS >= 16) & (HOURS < 21), 0.50, 0.25))
PEAK: Final = (HOURS >= 16) & (HOURS < 21)


def _grid() -> GridConfigData:
    return GridConfigData(
        element_type=ElementType.GRID,
        name="grid",
        connection=as_connection_target("switchboard"),
        pricing={"price_source_target": PRICE, "price_target_source": np.zeros(24)},
        power_limits={"max_power_source_target": np.full(24, 20.0), "max_power_target_source": np.zeros(24)},
    )


def _junction(name: str) -> JunctionConfigData:
    return JunctionConfigData(element_type=ElementType.JUNCTION, name=name)


def _connection(
    name: str,
    source: str,
    target: str,
    *,
    max_power: float | None = None,
    efficiency: float | None = None,
    draws_from_target: bool = False,
    conductance: float | None = None,
) -> ConnectionConfigData:
    return ConnectionConfigData(
        element_type=ElementType.CONNECTION,
        name=name,
        endpoints={"source": as_connection_target(source), "target": as_connection_target(target)},
        power_limits={} if max_power is None else {"max_power_source_target": np.full(24, max_power)},
        pricing={},
        efficiency={}
        if efficiency is None
        else {"efficiency_source_target": np.full(24, efficiency), "draws_from_target": draws_from_target},
        level={} if conductance is None else {"conductance": np.full(24, conductance)},
    )


def _thermal_mass(
    name: str,
    *,
    heat_capacity: float,
    temperature: float,
    ambient: NDArray[np.float64] | float,
    heat_loss: float,
    min_temperature: float,
    max_temperature: float,
) -> ThermalMassConfigData:
    return ThermalMassConfigData(
        element_type=ElementType.THERMAL_MASS,
        name=name,
        storage={"heat_capacity": heat_capacity, "temperature": temperature},
        comfort={
            "min_temperature": np.full(25, min_temperature),
            "max_temperature": np.full(25, max_temperature),
            "comfort_cost": 1.0,
        },
        surroundings={"ambient_temperature": np.broadcast_to(ambient, (24,)).astype(float), "heat_loss": heat_loss},
    )


def _optimize(participants: list[ElementConfigData]) -> Network:
    network = build_network("thermal", {config["name"]: config for config in participants}, [3600.0] * 24)
    network.optimize()
    return network


def _temperatures(network: Network, name: str) -> NDArray[np.float64]:
    store = network.elements[name]
    assert isinstance(store, Battery)
    return np.array(store.extract_values(store.end_level))


def _power(network: Network, name: str) -> NDArray[np.float64]:
    connection = network.elements[name]
    assert isinstance(connection, Connection)
    return np.array(connection.extract_values(connection.total_measured_power))


def test_hot_water_tank_heats_before_draws_and_never_in_the_peak() -> None:
    """A tank heats on cheap power ahead of the hot water it supplies, and not while power is dear."""
    draws = np.zeros(24)
    draws[7] = 4.0
    draws[19] = 5.0
    network = _optimize(
        [
            _grid(),
            _junction("switchboard"),
            _thermal_mass(
                "tank",
                heat_capacity=0.29,
                temperature=50.0,
                ambient=20.0,
                heat_loss=0.0011,
                min_temperature=45.0,
                max_temperature=65.0,
            ),
            _connection("heat pump", "switchboard", "tank", max_power=1.0, efficiency=3.0),
            LoadConfigData(
                element_type=ElementType.LOAD,
                name="hot water",
                connection=as_connection_target("tank"),
                forecast={"forecast": draws},
                curtailment={},
            ),
        ]
    )

    heating = _power(network, "heat pump")
    temperatures = _temperatures(network, "tank")
    assert np.all(heating[PEAK] < 1e-6)
    assert heating[HOURS < 6].sum() > 0.0
    assert np.all(temperatures >= 45.0 - 1e-6)
    assert np.all(temperatures <= 65.0 + 1e-6)


def test_rooms_precool_before_the_peak_without_heating_and_cooling_at_once() -> None:
    """Coupled rooms sharing an outdoor unit are cooled ahead of the peak, and no room is heated while it is cooled."""
    outdoor = 31.0 + 7.0 * np.sin((HOURS - 9) / 24 * 2 * np.pi)
    rooms = ["lounge", "bedroom"]
    participants: list[ElementConfigData] = [
        _grid(),
        _junction("switchboard"),
        _junction("ac"),
        _connection("outdoor unit", "switchboard", "ac", max_power=2.5),
        _connection("wall", "lounge", "bedroom", conductance=0.3),
    ]
    for room in rooms:
        participants += [
            _thermal_mass(
                room,
                heat_capacity=2.0,
                temperature=24.0,
                ambient=outdoor,
                heat_loss=0.15,
                min_temperature=21.0,
                max_temperature=25.0,
            ),
            _connection(f"cool {room}", "ac", room, max_power=1.2, efficiency=3.0, draws_from_target=True),
            _connection(f"heat {room}", "ac", room, max_power=1.2, efficiency=3.5),
        ]
    network = _optimize(participants)

    unit = _power(network, "outdoor unit")
    # The peak's first hours coast on cooling done before it
    assert np.all(unit[16:19] < 1e-6)
    assert unit[10:16].sum() > 0.0
    for room in rooms:
        assert np.all(_power(network, f"heat {room}") < 1e-6)
        assert np.all(_temperatures(network, room) <= 25.0 + 1e-6)
