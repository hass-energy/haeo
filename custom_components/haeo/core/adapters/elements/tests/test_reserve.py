"""Tests for the reserve adapter and the reserve it builds in the optimization."""

from collections.abc import Sequence
from typing import Final

import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.core.adapters.elements.headroom import (
    HEADROOM_ENERGY_AVAILABLE,
    HEADROOM_ENERGY_REQUIRED,
    HEADROOM_ENERGY_SHORTFALL,
    HEADROOM_STATE_OF_CHARGE,
)
from custom_components.haeo.core.adapters.elements.reserve import (
    RESERVE_DEVICE_RESERVE,
    RESERVE_ENERGY_AVAILABLE,
    RESERVE_ENERGY_REQUIRED,
    RESERVE_ENERGY_SHORTFALL,
    RESERVE_STATE_OF_CHARGE,
)
from custom_components.haeo.core.adapters.elements.reserve import adapter as reserve_adapter
from custom_components.haeo.core.adapters.policy_compilation import compile_policies
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES, collect_model_elements
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import Reserve
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.core.schema.elements.battery import BatteryConfigData
from custom_components.haeo.core.schema.elements.grid import GridConfigData
from custom_components.haeo.core.schema.elements.headroom import HeadroomConfigData
from custom_components.haeo.core.schema.elements.load import LoadConfigData
from custom_components.haeo.core.schema.elements.reserve import ReserveConfigData
from custom_components.haeo.core.schema.elements.solar import SolarConfigData

from .conftest import bus_node

N_PERIODS: Final = 4


def _battery(name: str, *, efficiency: float = 1.0) -> BatteryConfigData:
    """Return a 10 kWh battery at half charge on the bus."""
    return BatteryConfigData(
        element_type=ElementType.BATTERY,
        name=name,
        connection=as_connection_target("bus"),
        storage={"capacity": np.full(N_PERIODS + 1, 10.0), "initial_charge_percentage": 0.5},
        limits={},
        power_limits={},
        pricing={"salvage_value": 0.0},
        efficiency={
            "efficiency_source_target": np.full(N_PERIODS, efficiency),
            "efficiency_target_source": np.full(N_PERIODS, 1.0),
        },
        partitioning={},
    )


def _grid(export_price: Sequence[float] = (0.5, 0.0, 0.0, 0.0)) -> GridConfigData:
    """Return a grid that sells cheaply after the first hour and by default pays well for exports in it."""
    return GridConfigData(
        element_type=ElementType.GRID,
        name="grid",
        connection=as_connection_target("bus"),
        pricing={
            "price_source_target": np.array([1.0, 0.1, 0.1, 0.1]),
            "price_target_source": np.asarray(export_price, dtype=float),
        },
        power_limits={},
    )


def _load(name: str, power: Sequence[float]) -> LoadConfigData:
    return LoadConfigData(
        element_type=ElementType.LOAD,
        name=name,
        connection=as_connection_target("bus"),
        forecast={"forecast": np.asarray(power, dtype=float)},
        curtailment={"curtailment": False},
    )


def _solar(power: Sequence[float], *, curtailment: bool = False) -> SolarConfigData:
    return SolarConfigData(
        element_type=ElementType.SOLAR,
        name="solar",
        connection=as_connection_target("bus"),
        forecast={"forecast": np.asarray(power, dtype=float)},
        curtailment={"curtailment": curtailment},
    )


def _reserve(
    *,
    loads: list[str],
    storage: list[str],
    generation: list[str] | None = None,
    window: float = 2.0,
    minimum: float = 0.0,
    shortfall_cost: float = 10.0,
) -> ReserveConfigData:
    return ReserveConfigData(
        element_type=ElementType.RESERVE,
        name="reserve",
        participants={"loads": loads, "generation": generation or [], "storage": storage},
        requirement={"window": window, "minimum": np.full(N_PERIODS + 1, minimum)},
        pricing={"shortfall_cost": np.full(N_PERIODS, shortfall_cost)},
    )


def _optimize(
    participants: Sequence[ElementConfigData], name: str = "reserve"
) -> tuple[Network, dict[str, OutputData]]:
    """Optimize hourly periods and return the network and the named element's outputs."""
    configs = {config["name"]: config for config in participants}
    network = Network(name="test", periods=np.ones(N_PERIODS))
    for element in compile_policies(collect_model_elements(configs), [])["elements"]:
        network.add(element)
    network.optimize()
    model_outputs = {name: element.outputs() for name, element in network.elements.items()}
    config = configs[name]
    adapter = ELEMENT_TYPES[config["element_type"]]
    outputs = adapter.outputs(name, model_outputs, config=config, participants=configs)
    return network, {str(output_name): output for device in outputs.values() for output_name, output in device.items()}


def _values(output: OutputData) -> NDArray[np.float64]:
    return np.asarray(output.values, dtype=float)


@pytest.mark.parametrize(
    ("shortfall_cost", "expected_after_selling"),
    [
        pytest.param(10.0, 2.0, id="expensive_reserve_is_held"),
        pytest.param(0.01, 0.0, id="cheap_reserve_is_sold"),
    ],
)
def test_reserve_is_held_while_shortfall_cost_outweighs_selling(
    shortfall_cost: float, expected_after_selling: float
) -> None:
    """Exporting the whole battery in the first hour is held back only by the shortfall cost."""
    _network, outputs = _optimize(
        [
            bus_node("bus"),
            _grid(),
            _battery("battery"),
            _load("house", [1.0] * N_PERIODS),
            _reserve(loads=["house"], storage=["battery"], shortfall_cost=shortfall_cost),
        ]
    )

    required = _values(outputs[RESERVE_ENERGY_REQUIRED])
    available = _values(outputs[RESERVE_ENERGY_AVAILABLE])
    np.testing.assert_allclose(required, [2.0, 2.0, 2.0, 1.0, 0.0])
    np.testing.assert_allclose(_values(outputs[RESERVE_STATE_OF_CHARGE]), [0.2, 0.2, 0.2, 0.1, 0.0])
    assert available[1] == pytest.approx(expected_after_selling)
    np.testing.assert_allclose(
        _values(outputs[RESERVE_ENERGY_SHORTFALL]), np.maximum(required - available, 0.0), atol=1e-9
    )


def test_reserve_shares_batteries_and_adds_extra_after_generation_and_losses() -> None:
    """Batteries hold the reserve together, delivering stored energy after discharge losses.

    Solar offsets the house in the first hour, and the extra reserve is held on top.
    """
    _network, outputs = _optimize(
        [
            bus_node("bus"),
            _grid(),
            _battery("first", efficiency=0.8),
            _battery("second", efficiency=0.8),
            _load("house", [2.0] * N_PERIODS),
            _solar([2.0, 0.0, 0.0, 0.0]),
            _reserve(loads=["house"], generation=["solar"], storage=["first", "second"], minimum=1.0),
        ]
    )

    required = _values(outputs[RESERVE_ENERGY_REQUIRED])
    np.testing.assert_allclose(required, [3.0, 5.0, 5.0, 3.0, 1.0])
    # Stored at 80% efficiency across 20 kWh of batteries
    np.testing.assert_allclose(_values(outputs[RESERVE_STATE_OF_CHARGE]), required / 0.8 / 20.0)
    np.testing.assert_allclose(_values(outputs[RESERVE_ENERGY_AVAILABLE])[0], 2 * 5.0 * 0.8)
    np.testing.assert_allclose(_values(outputs[RESERVE_ENERGY_AVAILABLE])[1:], required[1:], atol=1e-9)


def test_reserve_keeps_its_shape_when_periods_and_window_change() -> None:
    """New period widths and windows rewrite the reserve's rows without adding any."""
    battery = _battery("battery")
    reserve_config = _reserve(loads=["house"], storage=["battery"])
    network, _outputs = _optimize(
        [bus_node("bus"), _grid(), battery, _load("house", [1.0] * N_PERIODS), reserve_config]
    )
    rows = network.constraints()["reserve"]

    network.update_periods(np.array([0.5, 1.0, 1.5, 1.0]))
    reserve = network.elements["reserve"]
    assert isinstance(reserve, Reserve)
    reserve.window = 1.25
    network.optimize()

    assert {name: len(cons) for name, cons in network.constraints()["reserve"].items() if isinstance(cons, list)} == {
        name: len(cons) for name, cons in rows.items() if isinstance(cons, list)
    }
    outputs = reserve_adapter.outputs(
        "reserve",
        {name: element.outputs() for name, element in network.elements.items()},
        config=reserve_config,
        participants={"battery": battery, "reserve": reserve_config},
    )[RESERVE_DEVICE_RESERVE]
    # 1 kW over 1.25 hours, cut short by the end of the horizon at the last boundaries
    np.testing.assert_allclose(_values(outputs[RESERVE_ENERGY_REQUIRED]), [1.25, 1.25, 1.25, 1.0, 0.0])


def _headroom(*, loads: list[str], generation: list[str], storage: list[str]) -> HeadroomConfigData:
    return HeadroomConfigData(
        element_type=ElementType.HEADROOM,
        name="headroom",
        participants={"loads": loads, "generation": generation, "storage": storage},
        requirement={"window": 4.0, "minimum": np.zeros(N_PERIODS + 1)},
        pricing={"shortfall_cost": np.full(N_PERIODS, 10.0)},
    )


@pytest.mark.parametrize("curtailment", [False, True], ids=["fixed_solar", "curtailable_solar"])
def test_headroom_makes_room_for_forecast_solar(curtailment: bool) -> None:
    """Headroom empties the battery before the solar arrives, even when curtailing the solar is free.

    Solar counts by its forecast, so curtailing it in the plan cannot shrink the headroom.
    The house uses some of the solar, which leaves less for the battery to absorb.
    """
    _network, outputs = _optimize(
        [
            bus_node("bus"),
            _grid(export_price=[0.0] * N_PERIODS),
            _battery("battery"),
            _load("house", [0.0, 0.0, 1.0, 1.0]),
            _solar([0.0, 0.0, 5.0, 5.0], curtailment=curtailment),
            _headroom(loads=["house"], generation=["solar"], storage=["battery"]),
        ],
        name="headroom",
    )

    required = _values(outputs[HEADROOM_ENERGY_REQUIRED])
    np.testing.assert_allclose(required, [8.0, 8.0, 8.0, 4.0, 0.0])
    np.testing.assert_allclose(_values(outputs[HEADROOM_ENERGY_SHORTFALL])[1:], 0.0, atol=1e-9)
    assert np.all(_values(outputs[HEADROOM_ENERGY_AVAILABLE])[1:] >= required[1:] - 1e-9)
    # The battery should stay below a full 10 kWh less the space it needs
    np.testing.assert_allclose(_values(outputs[HEADROOM_STATE_OF_CHARGE]), 1.0 - required / 10.0)
