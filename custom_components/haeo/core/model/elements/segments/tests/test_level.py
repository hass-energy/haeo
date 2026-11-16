"""Tests for level segments, which set flows from the level difference between a connection's ends."""

import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
    MODEL_ELEMENT_TYPE_NODE,
    Battery,
    Connection,
    ConnectionOutputName,
)
from custom_components.haeo.core.model.network import Network

# A store of heat whose level is its temperature: 1 kWh per °C, at 20 °C when empty
CAPACITY_PER_DEGREE = 1.0
EMPTY_TEMPERATURE = 20.0


def _store(network: Network, name: str, temperature: float) -> Battery:
    """Add a store of heat at the given temperature."""
    return network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
            "name": name,
            "capacity": 100.0,
            "initial_charge": (temperature - EMPTY_TEMPERATURE) * CAPACITY_PER_DEGREE,
            "level_offset": EMPTY_TEMPERATURE,
            "energy_per_level": CAPACITY_PER_DEGREE,
        }
    )


def _temperatures(store: Battery) -> NDArray[np.float64]:
    """Return the store's temperature at the end of each period in the solved plan."""
    return np.array(store.extract_values(store.end_level))


def _flow(connection: Connection[ConnectionOutputName]) -> NDArray[np.float64]:
    """Return the flow entering the connection in the solved plan."""
    return np.array(connection.extract_values(connection.total_power_in))


@pytest.mark.parametrize("period", [0.01, 1.0, 1000.0])
def test_conduction_decays_toward_the_surroundings_without_overshoot(period: float) -> None:
    """A store leaking to its surroundings follows the implicit decay and never passes them, however long the period."""
    network = Network(name="decay", periods=np.full(3, period))
    tank = _store(network, "tank", 60.0)
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "air", "level": EMPTY_TEMPERATURE})
    conductance = 0.1
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "loss",
            "source": "tank",
            "target": "air",
            "tags": {1},
            "segments": {"conduction": {"segment_type": "conduction", "conductance": conductance}},
        }
    )

    network.optimize()

    decay = 1.0 / (1.0 + conductance * period / CAPACITY_PER_DEGREE)
    expected = EMPTY_TEMPERATURE + 40.0 * decay ** np.arange(1, 4)
    assert _temperatures(tank) == pytest.approx(expected)


def test_conduction_tracks_exponential_decay_for_short_periods() -> None:
    """With periods far shorter than the time constant, the decay matches the continuous solution."""
    periods = np.full(1000, 0.01)
    network = Network(name="decay", periods=periods)
    tank = _store(network, "tank", 60.0)
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "air", "level": EMPTY_TEMPERATURE})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "loss",
            "source": "tank",
            "target": "air",
            "tags": {1},
            "segments": {"conduction": {"segment_type": "conduction", "conductance": 0.1}},
        }
    )

    network.optimize()

    assert _temperatures(tank)[-1] == pytest.approx(EMPTY_TEMPERATURE + 40.0 * np.exp(-1.0), rel=1e-3)


def test_conduction_runs_backward_when_the_target_is_higher() -> None:
    """Heat flows from the warmer room into the cooler one through a connection pointing the other way."""
    network = Network(name="rooms", periods=np.full(4, 1000.0))
    cool = _store(network, "cool", 22.0)
    warm = _store(network, "warm", 30.0)
    wall = network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "wall",
            "source": "cool",
            "target": "warm",
            "tags": {1},
            "segments": {"conduction": {"segment_type": "conduction", "conductance": 0.5}},
        }
    )

    network.optimize()

    assert _flow(wall)[0] < 0.0
    # Long periods settle both rooms at the mean of their temperatures, weighted by heat capacity
    assert _temperatures(cool)[-1] == pytest.approx(26.0, abs=1e-3)
    assert _temperatures(warm)[-1] == pytest.approx(26.0, abs=1e-3)


def test_level_limit_caps_delivery_by_the_level_difference() -> None:
    """A coil delivers at most its conductance times the gap between the tank and the water it heats."""
    network = Network(name="coil", periods=np.full(4, 1.0))
    tank = _store(network, "tank", 60.0)
    network.add(
        {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "tap", "is_source": False, "level": EMPTY_TEMPERATURE}
    )
    conductance = 2.0
    coil = network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "coil",
            "source": "tank",
            "target": "tap",
            "tags": {1},
            "segments": {
                "level_limit": {"segment_type": "level_limit", "conductance": conductance, "violation_price": 100.0},
                # Hot water is worth more than anything else, so the plan draws all the coil allows
                "pricing": {"segment_type": "pricing", "price": -1.0},
            },
        }
    )

    network.optimize()

    delivered = _flow(coil)
    temperatures = _temperatures(tank)
    assert delivered == pytest.approx(conductance * (temperatures - EMPTY_TEMPERATURE))
    assert np.all(np.diff(delivered) < 0.0)


def test_negative_efficiency_removes_energy_from_the_target() -> None:
    """A connection with efficiency below zero draws power at its source and takes energy from its target."""
    network = Network(name="cooling", periods=np.array([1.0]))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_sink": False})
    room = _store(network, "room", 30.0)
    cooler = network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "cooler",
            "source": "grid",
            "target": "room",
            "tags": {1},
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": 1.0, "fixed": True},
                "efficiency": {"segment_type": "efficiency", "efficiency": -3.0},
            },
        }
    )

    network.optimize()

    assert _flow(cooler) == pytest.approx([1.0])
    assert _temperatures(room) == pytest.approx([27.0])


def test_level_segment_requires_a_level_at_both_ends() -> None:
    """Joining an element without a level through a level segment is a configuration error."""
    network = Network(name="no_level", periods=np.array([1.0]))
    _store(network, "tank", 60.0)
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
            "name": "heater",
            "in_window": np.zeros(1),
            "window_start": np.zeros(1),
            "opened": np.zeros(1),
            "due": np.zeros(1),
            "deficit_price": np.zeros(1),
            "overage_price": np.zeros(1),
            "is_source": False,
            "is_sink": True,
        }
    )

    with pytest.raises(TypeError, match="must have levels"):
        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": "coil",
                "source": "tank",
                "target": "heater",
                "tags": {1},
                "segments": {"conduction": {"segment_type": "conduction", "conductance": 1.0}},
            }
        )


def test_target_level_replaces_the_level_of_the_target() -> None:
    """A coil feeding a tap whose node has no temperature of its own uses the inlet temperature it is given."""
    network = Network(name="coil", periods=np.full(2, 1.0))
    tank = _store(network, "tank", 60.0)
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "tap", "is_source": False})
    coil = network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "coil",
            "source": "tank",
            "target": "tap",
            "tags": {1},
            "segments": {
                "level_limit": {
                    "segment_type": "level_limit",
                    "conductance": 1.0,
                    "violation_price": 100.0,
                    "target_level": 40.0,
                },
                "pricing": {"segment_type": "pricing", "price": -1.0},
            },
        }
    )

    network.optimize()

    assert _flow(coil) == pytest.approx(_temperatures(tank) - 40.0)


def test_level_limit_below_zero_costs_rather_than_forcing_levels_apart() -> None:
    """A tank colder than the water its coil heats stays feasible, paying for the shortfall in its cap."""
    network = Network(name="cold_tank", periods=np.array([1.0]))
    tank = _store(network, "tank", 20.0)
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "tap", "is_source": False, "level": 30.0})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "coil",
            "source": "tank",
            "target": "tap",
            "tags": {1},
            "segments": {
                "level_limit": {"segment_type": "level_limit", "conductance": 0.5, "violation_price": 2.0},
            },
        }
    )

    cost = network.optimize()

    assert _temperatures(tank) == pytest.approx([20.0])
    # The cap is 0.5 kW/°C times -10 °C, so the plan pays for 5 kWh over it
    assert cost == pytest.approx(10.0)


def test_level_limit_with_no_conductance_constrains_no_level() -> None:
    """A period whose conductance is zero allows no flow and costs nothing however the levels sit."""
    network = Network(name="damper", periods=np.array([1.0, 1.0]))
    room = _store(network, "room", 25.0)
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "outside"})
    damper = network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "damper",
            "source": "room",
            "target": "outside",
            "tags": {1},
            "segments": {
                "level_limit": {
                    "segment_type": "level_limit",
                    "conductance": np.array([0.5, 0.0]),
                    "violation_price": 100.0,
                    "target_level": np.array([20.0, 30.0]),
                },
                # Cooling the room is worth something, so the plan opens the damper wherever it can
                "pricing": {"segment_type": "pricing", "price": -0.01},
            },
        }
    )

    cost = network.optimize()

    flows = _flow(damper)
    assert flows[0] == pytest.approx(0.5 * (_temperatures(room)[0] - 20.0))
    assert flows[1] == pytest.approx(0.0)
    assert cost == pytest.approx(-0.01 * flows[0])
