"""Tests for deferrable load element model mapping and optimization behavior."""

from typing import Any

import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.deferrable_load import (
    DEFERRABLE_ENERGY_ABSORBED,
    DEFERRABLE_ENERGY_DEFICIT,
    DEFERRABLE_LOAD_DEVICE,
    DEFERRABLE_POWER,
    adapter,
)
from custom_components.haeo.core.data.loader.calendar_resolver import CalendarBoundaryData
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.deferrable_load import (
    DEFERRABLE_LOAD_ENERGY_ABSORBED,
    DEFERRABLE_LOAD_ENERGY_DEFICIT,
)
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.deferrable_load import DeferrableLoadConfigData


def _boundary_data(
    presence: list[float],
    value_edge_start: list[float],
    value_edge_end: list[float],
) -> CalendarBoundaryData:
    """Build calendar boundary data with a derived value_span."""
    return CalendarBoundaryData(
        presence=np.array(presence, dtype=np.float64),
        value_span=np.array(presence, dtype=np.float64),
        value_edge_start=np.array(value_edge_start, dtype=np.float64),
        value_edge_end=np.array(value_edge_end, dtype=np.float64),
    )


def _config(**overrides: Any) -> DeferrableLoadConfigData:
    """Build a deferrable load config with a window in period 2."""
    config: dict[str, Any] = {
        "element_type": ElementType.DEFERRABLE_LOAD,
        "name": "pump",
        "connection": as_connection_target("home"),
        "schedule": {
            "window_calendar": _boundary_data(
                presence=[0.0, 0.0, 1.0, 0.0, 0.0],
                value_edge_start=[0.0, 0.0, 6.0, 0.0, 0.0],
                value_edge_end=[0.0, 0.0, 0.0, 6.0, 0.0],
            ),
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
    """The adapter creates the load and its window-gated connection."""
    elements = _elements_by_name(_config(power={"max_power": 1.5}))

    assert set(elements) == {"pump", "pump:connection"}
    load = elements["pump"]
    assert load["element_type"] == "deferrable_load"
    np.testing.assert_allclose(load["capacity"], [0.0, 0.0, 6.0, 6.0, 6.0])
    np.testing.assert_allclose(load["required"], [0.0, 0.0, 0.0, 6.0, 6.0])
    assert load["deficit_price"] == pytest.approx(10.0)

    connection = elements["pump:connection"]
    assert connection["source"] == "home"
    assert connection["target"] == "pump"
    # Power may only flow while the window is open (period 2).
    np.testing.assert_allclose(
        connection["segments"]["power_limit"]["max_power"],
        [0.0, 0.0, 1.5, 0.0],
    )


def test_unlimited_power_when_unconfigured() -> None:
    """Without a max power the window gate alone limits flow."""
    elements = _elements_by_name(_config())

    max_power = elements["pump:connection"]["segments"]["power_limit"]["max_power"]
    assert max_power[2] > 1e5
    np.testing.assert_allclose(max_power[[0, 1, 3]], [0.0, 0.0, 0.0])


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


def test_window_energy_absorbed_within_window() -> None:
    """The load absorbs its window energy inside the window."""
    network = _solve(_config(power={"max_power": 10.0}), grid_price=[0.1, 0.1, 0.1, 0.1])

    load_outputs = network.elements["pump"].outputs()
    absorbed = load_outputs[DEFERRABLE_LOAD_ENERGY_ABSORBED].values
    np.testing.assert_allclose(absorbed, [0.0, 0.0, 0.0, 6.0, 6.0])
    assert load_outputs[DEFERRABLE_LOAD_ENERGY_DEFICIT].values[-1] == pytest.approx(0.0)


def test_too_small_window_prices_the_shortfall() -> None:
    """When the device cannot absorb enough in the window, the deficit is priced."""
    config = _config(power={"max_power": 2.0}, pricing={"deficit_price": 5.0})
    network = _solve(config, grid_price=[0.1, 0.1, 0.1, 0.1])

    load_outputs = network.elements["pump"].outputs()
    absorbed = load_outputs[DEFERRABLE_LOAD_ENERGY_ABSORBED].values
    deficit = load_outputs[DEFERRABLE_LOAD_ENERGY_DEFICIT].values
    assert absorbed[-1] == pytest.approx(2.0)  # 2 kW for the one-hour window
    assert deficit[-1] == pytest.approx(4.0)


def test_outputs_mapping() -> None:
    """Adapter outputs expose power, absorbed energy, and the shortfall."""
    config = _config(power={"max_power": 10.0})
    network = _solve(config, grid_price=[0.1, 0.1, 0.1, 0.1])
    model_outputs = {name: element.outputs() for name, element in network.elements.items()}

    outputs = adapter.outputs("pump", model_outputs, config=config)[DEFERRABLE_LOAD_DEVICE]

    assert set(outputs) == {DEFERRABLE_POWER, DEFERRABLE_ENERGY_ABSORBED, DEFERRABLE_ENERGY_DEFICIT}
    assert outputs[DEFERRABLE_ENERGY_ABSORBED].values[-1] == pytest.approx(6.0)
    assert outputs[DEFERRABLE_ENERGY_DEFICIT].values[-1] == pytest.approx(0.0)
    np.testing.assert_allclose(outputs[DEFERRABLE_POWER].values, [0.0, 0.0, 6.0, 0.0])


@pytest.mark.parametrize(
    ("pricing", "expected_absorbed"),
    [
        # A clamped zero shortfall price leaves nothing worth buying grid energy for.
        pytest.param({"deficit_price": np.array([-5.0, -5.0, -5.0, -5.0])}, 0.0, id="negative_deficit_price"),
        # A clamped zero overage price still stops at the requirement.
        pytest.param({"deficit_price": 10.0, "overage_price": -1.0}, 6.0, id="negative_overage_price"),
    ],
)
def test_negative_prices_are_clamped_to_zero(pricing: dict[str, Any], expected_absorbed: float) -> None:
    """Negative penalty prices from an entity cannot make the optimization unbounded."""
    config = _config(power={"max_power": 10.0}, pricing=pricing)
    network = _solve(config, grid_price=[0.1, 0.1, 0.1, 0.1])

    load_outputs = network.elements["pump"].outputs()
    absorbed = load_outputs[DEFERRABLE_LOAD_ENERGY_ABSORBED].values[-1]
    deficit = load_outputs[DEFERRABLE_LOAD_ENERGY_DEFICIT].values[-1]
    assert absorbed == pytest.approx(expected_absorbed)
    assert deficit == pytest.approx(6.0 - expected_absorbed)


def _open_window_config(**schedule: Any) -> DeferrableLoadConfigData:
    """Build a config whose 6 kWh window is already open at the horizon start."""
    return _config(
        power={"max_power": 10.0},
        schedule={
            "window_calendar": _boundary_data(
                presence=[1.0, 1.0, 1.0, 0.0, 0.0],
                value_edge_start=[6.0, 0.0, 0.0, 0.0, 0.0],
                value_edge_end=[0.0, 0.0, 6.0, 0.0, 0.0],
            ),
            **schedule,
        },
    )


def test_energy_delivered_in_open_window_counts_toward_requirement() -> None:
    """Energy already delivered in the open window is not demanded again."""
    network = _solve(_open_window_config(energy_delivered=4.0), grid_price=[0.1, 0.1, 0.1, 0.1])

    load_outputs = network.elements["pump"].outputs()
    absorbed = load_outputs[DEFERRABLE_LOAD_ENERGY_ABSORBED].values
    assert absorbed[0] == pytest.approx(4.0)
    assert absorbed[-1] - absorbed[0] == pytest.approx(2.0)
    assert load_outputs[DEFERRABLE_LOAD_ENERGY_DEFICIT].values[-1] == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("config", "expected_initial"),
    [
        pytest.param(_open_window_config(), 0.0, id="unconfigured"),
        pytest.param(_open_window_config(energy_delivered=4.0), 4.0, id="open_window"),
        pytest.param(_open_window_config(energy_delivered=10.0), 6.0, id="clamped_to_open_window"),
        pytest.param(_open_window_config(energy_delivered=-1.0), 0.0, id="negative_reading"),
        pytest.param(
            _config(schedule={**_config()["schedule"], "energy_delivered": 4.0}),
            0.0,
            id="no_open_window",
        ),
    ],
)
def test_energy_delivered_sets_initial_energy(config: DeferrableLoadConfigData, expected_initial: float) -> None:
    """Delivered energy only applies to windows open at the horizon start."""
    load = _elements_by_name(config)["pump"]

    assert load["initial_energy"] == pytest.approx(expected_initial)
