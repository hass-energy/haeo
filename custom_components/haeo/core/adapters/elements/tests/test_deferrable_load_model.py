"""Tests for deferrable load element model mapping and optimization behavior."""

import numpy as np
from numpy.typing import NDArray
import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.adapters.elements.deferrable_load import (
    DEFERRABLE_ENERGY_DELIVERED,
    DEFERRABLE_ENERGY_OVERAGE,
    DEFERRABLE_ENERGY_SHORTFALL,
    DEFERRABLE_LOAD_DEVICE,
    DEFERRABLE_POWER,
    adapter,
)
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE
from custom_components.haeo.core.data.loader.config_loader import load_element_config
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
    MODEL_ELEMENT_TYPE_NODE,
    ConnectionElementConfig,
)
from custom_components.haeo.core.model.elements.deferrable_load import (
    DEFERRABLE_LOAD_ENERGY_DELIVERED,
    DEFERRABLE_LOAD_ENERGY_SHORTFALL,
    DEFERRABLE_LOAD_POWER,
    DeferrableLoadElementConfig,
)
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.deferrable_load import (
    DeferrableLoadConfigData,
    DeferrableLoadConfigSchema,
)


def _window(n_periods: int, start: int, end: int, energy: float) -> dict[str, NDArray[np.float64]]:
    """Build the loaded window inputs for one event over periods ``start`` to ``end``, due ``energy``.

    An event starting before the horizon is open at its start, so its window
    does not start and it opens at boundary 0.
    """
    in_window = np.zeros(n_periods)
    in_window[max(start, 0) : end] = 1.0
    window_start = np.zeros(n_periods + 1)
    if start > 0:
        window_start[start] = 1.0
    opened = np.zeros(n_periods + 1)
    opened[max(start, 0)] = energy
    due = np.zeros(n_periods + 1)
    due[end] = energy
    return {"in_window": in_window, "window_start": window_start, "opened": opened, "due": due}


def _prices(deficit: float = 10.0, overage: float = 0.0) -> dict[str, NDArray[np.float64]]:
    """Build loaded per-boundary prices over the four-period horizon."""
    return {"deficit_price": np.full(5, deficit), "overage_price": np.full(5, overage)}


def _config(**overrides: object) -> DeferrableLoadConfigData:
    """Build a deferrable load config with a window in period 2."""
    config: dict[str, object] = {
        "element_type": ElementType.DEFERRABLE_LOAD,
        "name": "pump",
        "connection": as_connection_target("home"),
        "schedule": {
            **_window(4, 2, 3, 6.0),
        },
        "pricing": {
            **_prices(),
        },
    }
    config.update(overrides)
    return config  # type: ignore[return-value]  # constructed to match DeferrableLoadConfigData


def _load(config: DeferrableLoadConfigData) -> DeferrableLoadElementConfig:
    """Return the deferrable load model element the adapter builds."""
    load, _connection = adapter.model_elements(config)
    assert load["element_type"] == MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD
    return load


def _connection(config: DeferrableLoadConfigData) -> ConnectionElementConfig:
    """Return the connection model element the adapter builds."""
    _load, connection = adapter.model_elements(config)
    assert connection["element_type"] == MODEL_ELEMENT_TYPE_CONNECTION
    return connection


def test_model_elements_structure() -> None:
    """The adapter creates the load and its connection."""
    config = _config(power={"max_power": 1.5})

    assert [element["name"] for element in adapter.model_elements(config)] == ["pump", "pump:connection"]
    load = _load(config)
    np.testing.assert_allclose(load["in_window"], [0.0, 0.0, 1.0, 0.0])
    np.testing.assert_allclose(load["window_start"], [0.0, 0.0, 1.0, 0.0, 0.0])
    np.testing.assert_allclose(load["opened"], [0.0, 0.0, 6.0, 0.0, 0.0])
    np.testing.assert_allclose(load["due"], [0.0, 0.0, 0.0, 6.0, 0.0])
    np.testing.assert_allclose(load["deficit_price"], 10.0)
    np.testing.assert_allclose(load["overage_price"], 0.0)

    connection = _connection(config)
    assert connection["source"] == "home"
    assert connection["target"] == "pump"
    assert connection.get("segments") == {"power_limit": {"segment_type": "power_limit", "max_power": 1.5}}


def test_no_power_limit_when_unconfigured() -> None:
    """Without a max power the connection has no limit; the load gates itself to its windows."""
    assert _connection(_config()).get("segments") == {}


def test_overage_price_reaches_the_model() -> None:
    """A configured overage price reaches the model as its per-boundary series."""
    overage = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
    config = _config(pricing={"deficit_price": np.full(5, 10.0), "overage_price": overage})

    np.testing.assert_allclose(_load(config)["overage_price"], overage)


def _solve(config: DeferrableLoadConfigData, grid_price: list[float]) -> Network:
    """Build and solve a grid + deferrable load network."""
    n = len(grid_price)
    network = Network(name="test", periods=np.array([1.0] * n))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "home", "is_source": False, "is_sink": False})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
    network.add(
        {
            "element_type": "connection",
            "name": "grid:import",
            "source": "grid",
            "target": "home",
            "tags": {1},
            "segments": {
                "pricing": {"segment_type": "pricing", "price": np.array(grid_price)},
            },
        }
    )
    # Policy compilation assigns tags in production; default them here.
    for element in adapter.model_elements(config):
        if element["element_type"] == "connection":
            element.setdefault("tags", {1})  # type: ignore[typeddict-unknown-key]  # spec allows tags
        network.add(element)
    network.optimize()
    return network


def test_window_energy_delivered_within_window() -> None:
    """The load receives its window energy inside the window."""
    network = _solve(_config(power={"max_power": 10.0}), grid_price=[0.1, 0.1, 0.1, 0.1])

    load_outputs = network.elements["pump"].outputs()
    np.testing.assert_allclose(load_outputs[DEFERRABLE_LOAD_ENERGY_DELIVERED].values, [0.0, 0.0, 0.0, 6.0, 0.0])
    assert load_outputs[DEFERRABLE_LOAD_ENERGY_SHORTFALL].values[3] == pytest.approx(0.0)


def test_power_stays_inside_windows_without_a_limit() -> None:
    """Without a power limit, cheap energy outside the window is still not used."""
    network = _solve(_config(), grid_price=[0.01, 0.01, 0.1, 0.01])

    np.testing.assert_allclose(
        network.elements["pump"].outputs()[DEFERRABLE_LOAD_POWER].values, [0.0, 0.0, 6.0, 0.0], atol=1e-9
    )


def test_too_small_window_prices_the_shortfall() -> None:
    """When the device cannot deliver enough in the window, the shortfall is priced."""
    config = _config(power={"max_power": 2.0}, pricing=_prices(deficit=5.0))
    network = _solve(config, grid_price=[0.1, 0.1, 0.1, 0.1])

    load_outputs = network.elements["pump"].outputs()
    assert load_outputs[DEFERRABLE_LOAD_ENERGY_DELIVERED].values[3] == pytest.approx(2.0)
    assert load_outputs[DEFERRABLE_LOAD_ENERGY_SHORTFALL].values[3] == pytest.approx(4.0)


def test_outputs_mapping() -> None:
    """Adapter outputs expose power, delivered energy, shortfall and overage."""
    config = _config(power={"max_power": 10.0})
    network = _solve(config, grid_price=[0.1, 0.1, 0.1, 0.1])
    model_outputs = {name: element.outputs() for name, element in network.elements.items()}

    outputs = adapter.outputs("pump", model_outputs, config=config)[DEFERRABLE_LOAD_DEVICE]

    assert set(outputs) == {
        DEFERRABLE_POWER,
        DEFERRABLE_ENERGY_DELIVERED,
        DEFERRABLE_ENERGY_SHORTFALL,
        DEFERRABLE_ENERGY_OVERAGE,
    }
    assert outputs[DEFERRABLE_ENERGY_DELIVERED].values[3] == pytest.approx(6.0)
    assert outputs[DEFERRABLE_ENERGY_SHORTFALL].values[3] == pytest.approx(0.0)
    assert outputs[DEFERRABLE_ENERGY_OVERAGE].values[3] == pytest.approx(0.0)
    np.testing.assert_allclose(outputs[DEFERRABLE_POWER].values, [0.0, 0.0, 6.0, 0.0])


def test_overage_above_the_energy_reward_stops_at_the_requirement() -> None:
    """An overage price above what the energy pays keeps the window at its requirement, even when paid to take more."""
    config = _config(power={"max_power": 10.0}, pricing=_prices(overage=1.0))
    network = _solve(config, grid_price=[-0.1, -0.1, -0.1, -0.1])

    assert network.elements["pump"].outputs()[DEFERRABLE_LOAD_ENERGY_DELIVERED].values[3] == pytest.approx(6.0)


def _open_window_config(**schedule: object) -> DeferrableLoadConfigData:
    """Build a config whose 6 kWh window is already open at the horizon start."""
    return _config(
        power={"max_power": 10.0},
        schedule={**_window(4, -1, 3, 6.0), **schedule},
    )


@pytest.mark.parametrize(
    ("energy_delivered", "expected_initial", "expected_new"),
    [
        pytest.param(None, 0.0, 6.0, id="unconfigured"),
        pytest.param(4.0, 4.0, 2.0, id="under_target"),
        pytest.param(10.0, 10.0, 0.0, id="over_target"),
    ],
)
def test_energy_delivered_seeds_the_open_window(
    energy_delivered: float | None, expected_initial: float, expected_new: float
) -> None:
    """Delivered energy seeds the open window; only the remainder is planned."""
    schedule = {} if energy_delivered is None else {"energy_delivered": energy_delivered}
    config = _open_window_config(**schedule)
    network = _solve(config, grid_price=[0.1, 0.1, 0.1, 0.1])

    delivered = network.elements["pump"].outputs()[DEFERRABLE_LOAD_ENERGY_DELIVERED].values
    assert delivered[0] == pytest.approx(expected_initial)
    assert delivered[3] - delivered[0] == pytest.approx(expected_new)
    shortfall = network.elements["pump"].outputs()[DEFERRABLE_LOAD_ENERGY_SHORTFALL].values
    assert shortfall[3] == pytest.approx(0.0)


def test_energy_delivered_never_seeds_a_later_window() -> None:
    """With no window open at the horizon start the delivered reading is ignored."""
    config = _config(power={"max_power": 10.0}, schedule={**_config()["schedule"], "energy_delivered": 4.0})
    network = _solve(config, grid_price=[0.1, 0.1, 0.1, 0.1])

    delivered = network.elements["pump"].outputs()[DEFERRABLE_LOAD_ENERGY_DELIVERED].values
    np.testing.assert_allclose(delivered, [0.0, 0.0, 0.0, 6.0, 0.0])


def test_config_loads_from_a_captured_calendar_state() -> None:
    """A deferrable load loaded from a calendar state carrying events reaches the model as its windows."""
    event = {
        "start": "1970-01-01T02:00:00+00:00",
        "end": "1970-01-01T03:00:00+00:00",
        "summary": "Pool pump",
        "location": "6 kWh",
        "description": None,
    }
    states = {"calendar.pool_pump": FakeEntityState("calendar.pool_pump", "off", {CALENDAR_EVENTS_ATTRIBUTE: [event]})}
    config: DeferrableLoadConfigSchema = {
        "element_type": ElementType.DEFERRABLE_LOAD,
        "name": "pump",
        "connection": as_connection_target("home"),
        "schedule": {"window_calendar": as_entity_value(["calendar.pool_pump"])},
        "pricing": {"deficit_price": as_constant_value(10.0), "overage_price": as_constant_value(0.0)},
    }

    loaded = load_element_config("pump", config, FakeStateMachine(states), (0.0, 3600.0, 7200.0, 10800.0, 14400.0))
    assert loaded["element_type"] == ElementType.DEFERRABLE_LOAD
    load = _load(loaded)

    np.testing.assert_allclose(load["in_window"], [0.0, 0.0, 1.0, 0.0])
    np.testing.assert_allclose(load["window_start"], [0.0, 0.0, 1.0, 0.0, 0.0])
    np.testing.assert_allclose(load["opened"], [0.0, 0.0, 6.0, 0.0, 0.0])
    np.testing.assert_allclose(load["due"], [0.0, 0.0, 0.0, 6.0, 0.0])
    np.testing.assert_allclose(load["deficit_price"], [10.0] * 5)
