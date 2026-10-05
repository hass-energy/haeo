"""Tests for deferrable load element model mapping and optimization behavior."""

from typing import Any

import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.deferrable_load import (
    DEFERRABLE_ENERGY_DELIVERED,
    DEFERRABLE_ENERGY_OVERAGE,
    DEFERRABLE_ENERGY_SHORTFALL,
    DEFERRABLE_LOAD_DEVICE,
    DEFERRABLE_POWER,
    adapter,
)
from custom_components.haeo.core.data.loader.calendar_resolver import CalendarBoundaryData
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.deferrable_load import (
    DEFERRABLE_LOAD_ENERGY_DELIVERED,
    DEFERRABLE_LOAD_ENERGY_SHORTFALL,
    DEFERRABLE_LOAD_POWER,
)
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.deferrable_load import DeferrableLoadConfigData


def _boundary_data(n_periods: int, events: list[tuple[int, int, float]]) -> CalendarBoundaryData:
    """Build calendar boundary data from period-aligned (start, end, value) events."""
    span = np.zeros(n_periods + 1)
    edge_start = np.zeros(n_periods + 1)
    edge_end = np.zeros(n_periods + 1)
    for start, end, value in events:
        span[max(start, 0) : min(end, n_periods + 1)] += value
        edge_start[max(start, 0)] += value
        if end <= n_periods:
            edge_end[end] += value
    return CalendarBoundaryData(
        presence=(span > 0).astype(np.float64),
        value_span=span,
        value_edge_start=edge_start,
        value_edge_end=edge_end,
        open_since=None,
    )


def _config(**overrides: Any) -> DeferrableLoadConfigData:
    """Build a deferrable load config with a window in period 2."""
    config: dict[str, Any] = {
        "element_type": ElementType.DEFERRABLE_LOAD,
        "name": "pump",
        "connection": as_connection_target("home"),
        "schedule": {
            "window_calendar": _boundary_data(4, [(2, 3, 6.0)]),
        },
        "pricing": {
            "deficit_price": 10.0,
        },
    }
    config.update(overrides)
    return config  # type: ignore[return-value]  # constructed to match DeferrableLoadConfigData


def _elements_by_name(config: DeferrableLoadConfigData) -> dict[str, dict[str, Any]]:
    return {element["name"]: dict(element) for element in adapter.model_elements(config)}


def test_model_elements_structure() -> None:
    """The adapter creates the load and its connection."""
    elements = _elements_by_name(_config(power={"max_power": 1.5}))

    assert set(elements) == {"pump", "pump:connection"}
    load = elements["pump"]
    assert load["element_type"] == "deferrable_load"
    np.testing.assert_allclose(load["in_window"], [0.0, 0.0, 1.0, 0.0])
    np.testing.assert_allclose(load["window_start"], [0.0, 0.0, 1.0, 0.0, 0.0])
    np.testing.assert_allclose(load["requirement"], [0.0, 0.0, 0.0, 6.0, 0.0])
    np.testing.assert_allclose(load["deficit_price"], 10.0)
    assert load["overage_price"] is None

    connection = elements["pump:connection"]
    assert connection["source"] == "home"
    assert connection["target"] == "pump"
    assert connection["segments"]["power_limit"]["max_power"] == pytest.approx(1.5)


def test_no_power_limit_when_unconfigured() -> None:
    """Without a max power the connection has no limit; the load gates itself to its windows."""
    elements = _elements_by_name(_config())

    assert elements["pump:connection"]["segments"] == {}


def test_overage_price_extends_to_boundaries() -> None:
    """A configured overage price reaches the model as a per-boundary series."""
    config = _config(pricing={"deficit_price": 10.0, "overage_price": np.array([0.1, 0.2, 0.3, 0.4])})

    load = _elements_by_name(config)["pump"]

    np.testing.assert_allclose(load["overage_price"], [0.1, 0.2, 0.3, 0.4, 0.4])


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
    config = _config(power={"max_power": 2.0}, pricing={"deficit_price": 5.0})
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


@pytest.mark.parametrize(
    ("pricing", "grid_price", "expected_delivered"),
    [
        # A clamped zero shortfall price leaves nothing worth buying grid energy for.
        pytest.param({"deficit_price": np.array([-5.0, -5.0, -5.0, -5.0])}, 0.1, 0.0, id="negative_deficit_price"),
        # A clamped zero overage price lets rewarded energy flow beyond the requirement.
        pytest.param({"deficit_price": 10.0, "overage_price": -1.0}, -0.1, 10.0, id="negative_overage_price"),
    ],
)
def test_negative_prices_are_clamped_to_zero(
    pricing: dict[str, Any], grid_price: float, expected_delivered: float
) -> None:
    """Negative penalty prices from an entity are clamped instead of rejected."""
    config = _config(power={"max_power": 10.0}, pricing=pricing)
    network = _solve(config, grid_price=[grid_price] * 4)

    delivered = network.elements["pump"].outputs()[DEFERRABLE_LOAD_ENERGY_DELIVERED].values[3]
    assert delivered == pytest.approx(expected_delivered)


def test_without_overage_price_delivery_is_capped() -> None:
    """With no overage price the window takes no more than its requirement, even when paid to."""
    network = _solve(_config(power={"max_power": 10.0}), grid_price=[-0.1, -0.1, -0.1, -0.1])

    assert network.elements["pump"].outputs()[DEFERRABLE_LOAD_ENERGY_DELIVERED].values[3] == pytest.approx(6.0)


def _open_window_config(**schedule: Any) -> DeferrableLoadConfigData:
    """Build a config whose 6 kWh window is already open at the horizon start."""
    return _config(
        power={"max_power": 10.0},
        schedule={"window_calendar": _boundary_data(4, [(-1, 3, 6.0)]), **schedule},
    )


@pytest.mark.parametrize(
    ("energy_delivered", "expected_initial", "expected_new"),
    [
        pytest.param(None, 0.0, 6.0, id="unconfigured"),
        pytest.param(4.0, 4.0, 2.0, id="under_target"),
        pytest.param(10.0, 10.0, 0.0, id="over_target"),
        pytest.param(-1.0, 0.0, 6.0, id="negative_reading"),
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
