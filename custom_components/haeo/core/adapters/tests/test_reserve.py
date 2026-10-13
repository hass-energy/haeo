"""Tests for the backup energy reserve."""

from collections.abc import Sequence
from typing import Final

import numpy as np
import pytest

from custom_components.haeo.core.adapters.reserve import apply_reserves, resolve_reserves, window_drawdown
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_reserve_value
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementConfigSchema, ElementType
from custom_components.haeo.core.schema.elements.battery import BatteryConfigData
from custom_components.haeo.core.schema.elements.load import LoadConfigData
from custom_components.haeo.core.schema.elements.solar import SolarConfigData

HOUR: Final = 3600.0
# Two one-hour periods
FORECAST_TIMES: Final[Sequence[float]] = (0.0, HOUR, 2 * HOUR)
UNDERCHARGE_PERCENTAGE: Final = ("undercharge", "percentage")


@pytest.mark.parametrize(
    ("net_energy", "window_hours", "expected"),
    [
        pytest.param([1.0, 1.0, 1.0, 1.0], 2.0, [2.0, 2.0, 2.0, 1.0, 0.0], id="steady_demand"),
        pytest.param([-2.0, 1.0, 1.0], 3.0, [0.0, 2.0, 1.0, 0.0], id="earlier_surplus_covers_later_demand"),
        pytest.param([1.0, 1.0, -3.0, 1.0], 3.0, [2.0, 1.0, 0.0, 1.0, 0.0], id="deepest_point_within_window"),
        pytest.param([2.0, 2.0], 1.5, [3.0, 2.0, 0.0], id="window_ends_mid_period"),
    ],
)
def test_window_drawdown(net_energy: list[float], window_hours: float, expected: list[float]) -> None:
    """The reserve is the deepest the energy balance falls below its start within the window."""
    boundaries = [index * HOUR for index in range(len(net_energy) + 1)]

    reserve = window_drawdown(np.array(net_energy), boundaries, window_hours * HOUR)

    np.testing.assert_allclose(reserve, expected)


def _battery(name: str, capacity: float, *, efficiency: float = 1.0, min_charge: float = 0.0) -> BatteryConfigData:
    return BatteryConfigData(
        element_type=ElementType.BATTERY,
        name=name,
        connection=as_connection_target("bus"),
        storage={"capacity": np.full(3, capacity), "initial_charge_percentage": 0.5},
        limits={"min_charge_percentage": min_charge},
        power_limits={},
        pricing={},
        efficiency={"efficiency_source_target": np.full(2, efficiency)},
        partitioning={},
    )


def _load(name: str, power: float, *, curtailment: bool = False) -> LoadConfigData:
    return LoadConfigData(
        element_type=ElementType.LOAD,
        name=name,
        connection=as_connection_target("bus"),
        forecast={"forecast": np.full(2, power)},
        curtailment={"curtailment": curtailment},
    )


def _solar(name: str, power: float) -> SolarConfigData:
    return SolarConfigData(
        element_type=ElementType.SOLAR,
        name=name,
        connection=as_connection_target("bus"),
        forecast={"forecast": np.full(2, power)},
        curtailment={"curtailment": True},
    )


def _reserve_schema(element_type: ElementType, window_hours: float) -> ElementConfigSchema:
    return {  # type: ignore[return-value]  # only the fields the reserve reads
        "element_type": element_type,
        "undercharge": {"percentage": as_reserve_value(window_hours), "cost": as_constant_value(0.1)},
    }


def test_resolve_reserves_covers_uncurtailable_loads_less_solar() -> None:
    """The level holds the net demand of loads that cannot be shed, after solar and discharge losses."""
    loaded: dict[str, ElementConfigData] = {
        "battery": _battery("battery", 10.0, efficiency=0.8, min_charge=0.1),
        "house": _load("house", 1.0),
        "pool": _load("pool", 5.0, curtailment=True),
        "solar": _solar("solar", 0.5),
    }
    participants = {"battery": _reserve_schema(ElementType.BATTERY, 1.0)}

    levels = resolve_reserves(participants, loaded, FORECAST_TIMES)

    # 0.5 kWh net demand over the next hour, stored at 80% efficiency in 10 kWh above the 10% floor
    np.testing.assert_allclose(levels[("battery", UNDERCHARGE_PERCENTAGE)], [0.1625, 0.1625, 0.1])


def test_resolve_reserves_shares_between_batteries_by_capacity() -> None:
    """Batteries holding the reserve together each hold a share proportional to their capacity."""
    loaded: dict[str, ElementConfigData] = {
        "small": _battery("small", 10.0),
        "large": _battery("large", 30.0),
        "house": _load("house", 4.0),
    }
    participants = {
        "small": _reserve_schema(ElementType.BATTERY, 2.0),
        "large": _reserve_schema(ElementType.BATTERY, 2.0),
    }

    levels = resolve_reserves(participants, loaded, FORECAST_TIMES)

    # 8 kWh over the window, a quarter held by the small battery and three quarters by the large one
    np.testing.assert_allclose(levels[("small", UNDERCHARGE_PERCENTAGE)], [0.2, 0.1, 0.0])
    np.testing.assert_allclose(levels[("large", UNDERCHARGE_PERCENTAGE)], [0.2, 0.1, 0.0])


def test_resolve_reserves_caps_level_at_full() -> None:
    """A reserve larger than the battery asks for a full battery."""
    loaded: dict[str, ElementConfigData] = {"battery": _battery("battery", 1.0), "house": _load("house", 4.0)}

    levels = resolve_reserves({"battery": _reserve_schema(ElementType.BATTERY, 2.0)}, loaded, FORECAST_TIMES)

    np.testing.assert_allclose(levels[("battery", UNDERCHARGE_PERCENTAGE)], [1.0, 1.0, 0.0])


def test_resolve_reserves_rejects_elements_that_cannot_hold_a_reserve() -> None:
    """Only elements whose adapter can hold a reserve may be configured with one."""
    loaded: dict[str, ElementConfigData] = {"house": _load("house", 1.0)}

    with pytest.raises(TypeError, match="cannot hold a reserve"):
        resolve_reserves({"house": _reserve_schema(ElementType.LOAD, 1.0)}, loaded, FORECAST_TIMES)


def test_apply_reserves_writes_levels_into_loaded_configs() -> None:
    """Reserve levels are written into the loaded config so the adapter sees them as the field value."""
    battery = _battery("battery", 10.0)
    undercharge: dict[str, object] = {"cost": 0.1}
    battery["undercharge"] = undercharge  # type: ignore[typeddict-item]  # filled in by apply_reserves
    loaded: dict[str, ElementConfigData] = {"battery": battery, "house": _load("house", 1.0)}

    apply_reserves({"battery": _reserve_schema(ElementType.BATTERY, 1.0)}, loaded, FORECAST_TIMES)

    np.testing.assert_allclose(undercharge["percentage"], [0.1, 0.1, 0.0])  # type: ignore[arg-type]
