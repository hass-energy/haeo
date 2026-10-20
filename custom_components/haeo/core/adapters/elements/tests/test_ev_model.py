"""Tests for EV element model mapping and trip optimization behavior."""

from typing import NamedTuple, TypedDict

import numpy as np
from numpy.typing import NDArray
import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.adapters.elements.ev import (
    DEFAULT_PUBLIC_CHARGING_PRICE,
    EV_DEVICE_EV,
    EV_ENERGY_STORED,
    EV_POWER_ACTIVE,
    EV_POWER_CHARGE,
    EV_POWER_DISCHARGE,
    EV_STATE_OF_CHARGE,
    EV_TRIP_ENERGY_DELIVERED,
    EV_TRIP_ENERGY_SHORTFALL,
    TRIP_OVERAGE_PRICE,
    adapter,
)
from custom_components.haeo.core.data.loader.calendar import CALENDAR_EVENTS_ATTRIBUTE
from custom_components.haeo.core.data.loader.config_loader import load_element_config
from custom_components.haeo.core.data.loader.meter import METER_TOTALS_ATTRIBUTE
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_BUFFER,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
    MODEL_ELEMENT_TYPE_NODE,
    BatteryElementConfig,
    ConnectionElementConfig,
)
from custom_components.haeo.core.model.elements.battery import BATTERY_ENERGY_STORED
from custom_components.haeo.core.model.elements.deferrable_load import (
    DEFERRABLE_LOAD_ENERGY_DELIVERED,
    DEFERRABLE_LOAD_ENERGY_OVERAGE,
    DEFERRABLE_LOAD_ENERGY_SHORTFALL,
    DeferrableLoadElementConfig,
)
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.ev import EvConfigData, EvConfigSchema

N_PERIODS = 4


def _trips(*trips: tuple[int, int, float], n: int = N_PERIODS) -> dict[str, object]:
    """Build the inputs the trip calendar feeds from trips given as (start, end, distance) boundaries.

    A trip starting at boundary 0 is the trip open at the horizon start: it
    opens there, but its window began before the horizon.
    """
    away = np.zeros(n)
    trip_start = np.zeros(n + 1)
    opened = np.zeros(n + 1)
    due = np.zeros(n + 1)
    for start, end, distance in trips:
        away[start:end] = 1.0
        trip_start[start] = float(start > 0)
        opened[start] += distance
        due[end] += distance
    return {"away": away, "trip_start": trip_start, "trip_opened": opened, "trip_due": due}


def _ev_config(*, plugged_in: bool = True, **overrides: object) -> EvConfigData:
    """Build an EV config with sensible defaults, applying overrides."""
    config: dict[str, object] = {
        "element_type": ElementType.EV,
        "name": "ev",
        "connection": as_connection_target("home"),
        "vehicle": {
            "capacity": np.array([50.0] * (N_PERIODS + 1)),
            "energy_per_distance": 0.2,
            "current_soc": 0.10,
        },
        "charging": {
            "max_charge_rate": 10.0,
            "connected": np.full(N_PERIODS, 1.0 if plugged_in else 0.0),
        },
        "efficiency": {},
        "advanced": {"charge_limit_cost": 100.0},
    }
    config.update(overrides)
    return config  # type: ignore[return-value]  # constructed to match EvConfigData


class _EvElements(NamedTuple):
    """The model elements an EV builds, in adapter order."""

    pack: BatteryElementConfig
    charge: ConnectionElementConfig
    discharge: ConnectionElementConfig
    trip: DeferrableLoadElementConfig
    trip_connection: ConnectionElementConfig


def _elements(config: EvConfigData) -> _EvElements:
    pack, charge, discharge, trip, trip_connection = adapter.model_elements(config)
    assert pack["element_type"] == MODEL_ELEMENT_TYPE_BATTERY
    assert charge["element_type"] == MODEL_ELEMENT_TYPE_CONNECTION
    assert discharge["element_type"] == MODEL_ELEMENT_TYPE_CONNECTION
    assert trip["element_type"] == MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD
    assert trip_connection["element_type"] == MODEL_ELEMENT_TYPE_CONNECTION
    return _EvElements(pack, charge, discharge, trip, trip_connection)


def _max_power(connection: ConnectionElementConfig) -> NDArray[np.float64] | float:
    """Return a connection's power limit."""
    segment = connection.get("segments", {})["power_limit"]
    assert segment["segment_type"] == "power_limit"
    max_power = segment.get("max_power")
    assert max_power is not None
    return max_power


def _home(config: EvConfigData) -> NDArray[np.float64]:
    """Return where the car is home: where its trip connection carries no power."""
    return np.asarray(_max_power(_elements(config).trip_connection)) == 0.0


# --- model_elements structure ---


def test_model_elements_structure() -> None:
    """The adapter creates the five expected model elements."""
    elements = _elements(_ev_config())

    assert [element["name"] for element in elements] == [
        "ev",
        "ev:charge",
        "ev:discharge",
        "ev:trip",
        "ev:trip_connection",
    ]
    assert elements.pack.get("initial_charge") == pytest.approx(5.0)  # SOC ratio 0.10 of 50 kWh
    assert elements.charge["source"] == "home"
    assert elements.charge["target"] == "ev"
    assert elements.trip_connection["target"] == "ev:trip"


def test_no_trip_config_yields_an_inert_trip_load() -> None:
    """Without a trip calendar the trip load has no windows and needs nothing."""
    trip = _elements(_ev_config()).trip

    np.testing.assert_array_equal(trip["in_window"], np.zeros(N_PERIODS))
    np.testing.assert_array_equal(trip["due"], np.zeros(N_PERIODS + 1))


@pytest.mark.parametrize(
    ("public_charging", "expected"),
    [
        pytest.param({}, DEFAULT_PUBLIC_CHARGING_PRICE, id="default"),
        pytest.param({"public_charging_price": 0.6}, 0.6, id="configured"),
    ],
)
def test_trip_shortfall_is_priced_at_the_public_charging_price(
    public_charging: dict[str, float], expected: float
) -> None:
    """The trip's shortfall price is the public charging price, high by default, and overage is priced high."""
    trip = _elements(_ev_config(public_charging=public_charging)).trip

    np.testing.assert_allclose(trip["deficit_price"], [expected] * (N_PERIODS + 1))
    np.testing.assert_allclose(trip["overage_price"], [TRIP_OVERAGE_PRICE] * (N_PERIODS + 1))


def test_calendar_drives_trip_energy_and_home_masks() -> None:
    """Trip distances become energy due at each trip's end, and home charging stops while away."""
    config = _ev_config(trip=_trips((2, 3, 30.0)))
    elements = _elements(config)

    np.testing.assert_allclose(elements.trip["opened"], [0.0, 0.0, 6.0, 0.0, 0.0])
    np.testing.assert_allclose(elements.trip["due"], [0.0, 0.0, 0.0, 6.0, 0.0])
    np.testing.assert_allclose(_max_power(elements.charge), [10.0, 10.0, 0.0, 10.0])
    np.testing.assert_array_equal(_home(config), [True, True, False, True])


@pytest.mark.parametrize("plugged_in", [True, False])
def test_plugged_in_sensor_pins_the_current_interval(*, plugged_in: bool) -> None:
    """The plugged-in sensor decides whether the car is home now; the calendar decides later periods."""
    config = _ev_config(plugged_in=plugged_in, trip=_trips((2, 3, 30.0)))

    np.testing.assert_array_equal(_home(config), [plugged_in, True, False, True])


def test_glitched_soc_sensor_is_clamped() -> None:
    """A state of charge outside 0-100% is clamped to the pack."""
    config = _ev_config()
    config["vehicle"]["current_soc"] = 1.7

    assert _elements(config).pack.get("initial_charge") == pytest.approx(50.0)


# --- The trip open at the horizon start ---


def test_plugged_in_without_driving_has_not_left_yet() -> None:
    """Plugged in during an open trip without having driven, the car is home now and the trip is still due."""
    config = _ev_config(trip={**_trips((0, 2, 30.0)), "odometer": 0.0})
    elements = _elements(config)

    np.testing.assert_array_equal(_home(config), [True, False, True, True])
    np.testing.assert_allclose(elements.trip["due"], [0.0, 0.0, 6.0, 0.0, 0.0])
    assert elements.trip.get("initial_energy") == 0.0


def test_plugged_in_after_driving_ends_the_trip_and_keeps_later_ones() -> None:
    """Plugged in after driving, the car is back: its trip is dropped, and later trips still happen."""
    config = _ev_config(trip={**_trips((0, 2, 30.0), (3, 4, 20.0)), "odometer": 12.0})
    elements = _elements(config)

    np.testing.assert_array_equal(_home(config), [True, True, True, False])
    np.testing.assert_allclose(elements.trip["opened"], [0.0, 0.0, 0.0, 4.0, 0.0])
    np.testing.assert_allclose(elements.trip["due"], [0.0, 0.0, 0.0, 0.0, 4.0])
    np.testing.assert_allclose(_max_power(elements.charge), [10.0, 10.0, 10.0, 0.0])


@pytest.mark.parametrize(
    ("odometer", "expected"),
    [
        pytest.param(None, 0.0, id="without_an_odometer"),
        pytest.param(10.0, 2.0, id="under_the_trip"),
        pytest.param(100.0, 6.0, id="beyond_the_trip_completes_it"),
    ],
)
def test_unplugged_on_a_trip_credits_the_distance_driven(odometer: float | None, expected: float) -> None:
    """Unplugged during an open trip, the energy for the distance driven counts toward it, up to the trip's own."""
    trip = _trips((0, 2, 30.0)) if odometer is None else {**_trips((0, 2, 30.0)), "odometer": odometer}
    config = _ev_config(plugged_in=False, trip=trip)

    assert _elements(config).trip.get("initial_energy") == pytest.approx(expected)
    np.testing.assert_array_equal(_home(config), [False, False, True, True])


def test_loads_an_open_trip_from_captured_states() -> None:
    """An EV loaded from captured states credits the distance driven since its open trip began."""
    start = 1_767_225_600.0
    trip = {
        "start": "2026-01-01T00:00:00+00:00",
        "end": "2026-01-01T03:00:00+00:00",
        "summary": "Beach",
        "location": "50 km",
        "description": None,
    }
    states = {
        "calendar.trips": FakeEntityState("calendar.trips", "on", {CALENDAR_EVENTS_ATTRIBUTE: [trip]}),
        "sensor.odometer": FakeEntityState(
            "sensor.odometer",
            "10030",
            {
                "unit_of_measurement": "km",
                "device_class": "distance",
                "state_class": "total_increasing",
                METER_TOTALS_ATTRIBUTE: [(start - 600.0, 400.0), (start, 400.0), (start + 3000.0, 430.0)],
            },
        ),
        "binary_sensor.plugged_in": FakeEntityState("binary_sensor.plugged_in", "off", {}),
        "sensor.soc": FakeEntityState("sensor.soc", "60", {"unit_of_measurement": "%"}),
    }
    config: EvConfigSchema = {
        "element_type": ElementType.EV,
        "name": "ev",
        "connection": as_connection_target("home"),
        "vehicle": {
            "capacity": as_constant_value(50.0),
            "energy_per_distance": as_constant_value(0.2),
            "current_soc": as_entity_value(["sensor.soc"]),
        },
        "charging": {
            "max_charge_rate": as_constant_value(7.0),
            "connected": as_entity_value(["binary_sensor.plugged_in"]),
        },
        "trip": {
            "trip_calendar": as_entity_value(["calendar.trips"]),
            "odometer": as_entity_value(["sensor.odometer"]),
        },
        "efficiency": {},
        "advanced": {"charge_limit_cost": as_constant_value(100.0)},
    }
    times = tuple(start + 3600.0 * k for k in range(1, N_PERIODS + 2))

    loaded = load_element_config("ev", config, FakeStateMachine(states), times)
    assert loaded["element_type"] == ElementType.EV
    trip_load = _elements(loaded).trip

    np.testing.assert_allclose(trip_load["window_start"], [0.0] * (N_PERIODS + 1))
    np.testing.assert_allclose(trip_load["opened"], [10.0, 0.0, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(trip_load["due"], [0.0, 0.0, 10.0, 0.0, 0.0])
    assert trip_load.get("initial_energy") == pytest.approx(6.0)


# --- End-to-end optimization behavior ---


def _solve_ev_network(config: EvConfigData, grid_price: list[float]) -> Network:
    """Build and solve a grid + EV network from the adapter's model elements."""
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
    ordered = sorted(adapter.model_elements(config), key=lambda e: e["element_type"] != "node")
    for element in ordered:
        if element["element_type"] == "connection":
            element.setdefault("tags", {1})  # type: ignore[typeddict-unknown-key]  # spec allows tags
        network.add(element)

    network.optimize()
    return network


def test_optimizer_precharges_before_trip_in_cheap_period() -> None:
    """The EV charges ahead of the trip when energy is cheapest."""
    network = _solve_ev_network(_ev_config(trip=_trips((2, 3, 30.0))), grid_price=[0.1, 0.5, 0.5, 0.5])

    trip_delivered = network.elements["ev:trip"].outputs()[DEFERRABLE_LOAD_ENERGY_DELIVERED].values
    assert trip_delivered[3] == pytest.approx(6.0, abs=1e-6)

    # The 1 kWh top-up (5 kWh initial vs 6 kWh trip) buys in the cheap period.
    ev_stored = network.elements["ev"].outputs()[BATTERY_ENERGY_STORED].values
    assert ev_stored[1] == pytest.approx(6.0, abs=1e-6)


def test_trips_stop_at_the_min_charge_and_leave_the_rest_to_public_charging() -> None:
    """A trip draws the pack down to its min charge, and the rest is a public top-up rather than draining past it."""
    config = _ev_config(
        charging={"max_charge_rate": 0.0, "connected": np.ones(N_PERIODS)},
        trip=_trips((1, 2, 50.0)),
    )
    config["vehicle"]["current_soc"] = 0.3
    config["vehicle"]["min_charge_percentage"] = np.full(N_PERIODS + 1, 0.2)
    network = _solve_ev_network(config, grid_price=[0.1, 0.1, 0.1, 0.1])

    stored = network.elements["ev"].outputs()[BATTERY_ENERGY_STORED].values
    assert min(stored) == pytest.approx(10.0)
    assert network.elements["ev:trip"].outputs()[DEFERRABLE_LOAD_ENERGY_SHORTFALL].values[2] == pytest.approx(5.0)


def test_trip_shortfall_is_left_to_public_charging() -> None:
    """When home charging cannot cover the trip, the rest is a shortfall rather than infeasible."""
    config = _ev_config(
        charging={"max_charge_rate": 2.0, "connected": np.ones(N_PERIODS)},
        trip=_trips((2, 3, 100.0)),
        public_charging={"public_charging_price": 0.8},
    )
    # Trip needs 20 kWh; pack holds 5 + at most 4 charged before departure.
    network = _solve_ev_network(config, grid_price=[0.1, 0.1, 0.1, 0.1])

    trip_outputs = network.elements["ev:trip"].outputs()
    assert trip_outputs[DEFERRABLE_LOAD_ENERGY_DELIVERED].values[3] == pytest.approx(9.0, abs=1e-6)
    assert trip_outputs[DEFERRABLE_LOAD_ENERGY_SHORTFALL].values[3] == pytest.approx(11.0, abs=1e-6)


def test_home_charge_limit_binds_at_the_charger() -> None:
    """The charge limit and charge power are measured at the charger, before charging losses."""
    config = _ev_config(
        charging={"max_charge_rate": 2.0, "connected": np.ones(N_PERIODS)},
        efficiency={"efficiency_target_source": 0.9},
        trip=_trips((2, 3, 100.0)),
    )
    network = _solve_ev_network(config, grid_price=[0.1, 0.1, 0.1, 0.1])
    model_outputs = {name: element.outputs() for name, element in network.elements.items()}

    outputs = adapter.outputs("ev", model_outputs, config=config)[EV_DEVICE_EV]

    # Both periods before departure charge at the 2 kW limit; 90% of it reaches the pack.
    np.testing.assert_allclose(outputs[EV_POWER_CHARGE].values[:2], [2.0, 2.0], atol=1e-6)
    np.testing.assert_allclose(outputs[EV_ENERGY_STORED].values[:3], [5.0, 6.8, 8.6], atol=1e-6)


def test_driving_beyond_the_trip_completes_it_at_no_cost() -> None:
    """A car that drove further than its trip has completed it: no shortfall, no overage, no more energy drawn."""
    config = _ev_config(plugged_in=False, trip={**_trips((0, 1, 30.0)), "odometer": 100.0})
    network = _solve_ev_network(config, grid_price=[0.1, 0.1, 0.1, 0.1])

    trip_outputs = network.elements["ev:trip"].outputs()
    np.testing.assert_allclose(trip_outputs[DEFERRABLE_LOAD_ENERGY_SHORTFALL].values, [0.0] * (N_PERIODS + 1))
    np.testing.assert_allclose(trip_outputs[DEFERRABLE_LOAD_ENERGY_OVERAGE].values, [0.0] * (N_PERIODS + 1))
    assert trip_outputs[DEFERRABLE_LOAD_ENERGY_DELIVERED].values[1] == pytest.approx(6.0)
    assert network.elements["ev:trip_connection"].outputs()["connection_power"].values[0] == pytest.approx(0.0)


def test_negative_prices_never_plan_driving_further_than_the_trip() -> None:
    """Being paid to use energy never empties a full pack into a trip to make room to charge again after it."""
    config = _ev_config(trip=_trips((1, 2, 30.0)))
    config["vehicle"]["capacity"] = np.full(N_PERIODS + 1, 10.0)
    network = _solve_ev_network(config, grid_price=[-1.0, -1.0, -1.0, -1.0])

    trip_outputs = network.elements["ev:trip"].outputs()
    assert trip_outputs[DEFERRABLE_LOAD_ENERGY_DELIVERED].values[2] == pytest.approx(6.0)
    np.testing.assert_allclose(trip_outputs[DEFERRABLE_LOAD_ENERGY_OVERAGE].values, [0.0] * (N_PERIODS + 1), atol=1e-9)


# --- Outputs mapping ---


def test_outputs_mapping_from_solved_network() -> None:
    """Adapter outputs map solved model values to EV output names."""
    config = _ev_config(trip=_trips((2, 3, 30.0)))
    network = _solve_ev_network(config, grid_price=[0.1, 0.5, 0.5, 0.5])
    model_outputs = {name: element.outputs() for name, element in network.elements.items()}

    outputs = adapter.outputs("ev", model_outputs, config=config)[EV_DEVICE_EV]

    assert outputs[EV_TRIP_ENERGY_DELIVERED].values[3] == pytest.approx(6.0, abs=1e-6)
    assert outputs[EV_TRIP_ENERGY_SHORTFALL].values[3] == pytest.approx(0.0, abs=1e-6)
    # SOC is derived from stored energy over pack capacity.
    assert outputs[EV_STATE_OF_CHARGE].values[0] == pytest.approx(0.10)
    # Active power is discharge minus charge for every period.
    np.testing.assert_allclose(
        outputs[EV_POWER_ACTIVE].values,
        np.asarray(outputs[EV_POWER_DISCHARGE].values) - np.asarray(outputs[EV_POWER_CHARGE].values),
    )


def test_state_of_charge_uses_capacity_at_each_boundary() -> None:
    """SOC divides each boundary's stored energy by that boundary's capacity."""
    config = _ev_config()
    config["vehicle"]["capacity"] = np.array([50.0, 50.0, 40.0, 25.0, 25.0])
    network = _solve_ev_network(config, grid_price=[0.1, 0.1, 0.1, 0.1])
    model_outputs = {name: element.outputs() for name, element in network.elements.items()}

    outputs = adapter.outputs("ev", model_outputs, config=config)[EV_DEVICE_EV]

    stored = np.asarray(outputs[EV_ENERGY_STORED].values)
    assert stored[3] > 0.0
    np.testing.assert_allclose(outputs[EV_STATE_OF_CHARGE].values, stored / config["vehicle"]["capacity"])


# --- Buffers ---


class _BufferSpec(TypedDict):
    loads: list[str]
    storage: list[str]
    window: float
    level: float | None


def _reserve(loads: list[str], storage: list[str], *, window: float = 2.0, level: float | None = None) -> _BufferSpec:
    return {"loads": loads, "storage": storage, "window": window, "level": level}


def _buffered_home_network(buffers: dict[str, _BufferSpec], *, trip_periods: tuple[int, int] = (3, 4)) -> Network:
    """Solve a house, a home battery, and a V2G EV with a 10 kWh trip under reserve buffers.

    Grid energy is cheapest in period 0. The trip covers periods ``trip_periods[0]`` up to ``trip_periods[1]``.
    """
    n = 4
    network = Network(name="test", periods=np.ones(n))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "home", "is_source": False, "is_sink": False})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": False})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "grid:import",
            "source": "grid",
            "target": "home",
            "tags": {1},
            "segments": {"pricing": {"segment_type": "pricing", "price": np.array([0.1, 0.3, 0.3, 0.3])}},
        }
    )
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "house", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "house:connection",
            "source": "home",
            "target": "house",
            "tags": {1},
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": np.ones(n), "fixed": True}},
        }
    )
    network.add(
        {"element_type": MODEL_ELEMENT_TYPE_BATTERY, "name": "battery", "capacity": 20.0, "initial_charge": 2.0}
    )
    for name, source, target in (("battery:charge", "home", "battery"), ("battery:discharge", "battery", "home")):
        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": name,
                "source": source,
                "target": target,
                "tags": {1},
                "segments": {"power_limit": {"segment_type": "power_limit", "max_power": 5.0}},
            }
        )
    config = _ev_config(
        charging={"max_charge_rate": 10.0, "max_discharge_rate": 10.0, "connected": np.ones(n)},
        trip=_trips((trip_periods[0], trip_periods[1], 50.0)),
    )
    for element in sorted(adapter.model_elements(config), key=lambda e: e["element_type"] != "node"):
        if element["element_type"] == "connection":
            element.setdefault("tags", {1})  # type: ignore[typeddict-unknown-key]  # spec allows tags
        network.add(element)
    for name, spec in buffers.items():
        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_BUFFER,
                "name": name,
                "kind": "reserve",
                "generation": [],
                "price": 1.0,
                **spec,
            }
        )
    network.optimize()
    return network


def test_buffer_counts_the_ev_trips_as_its_load() -> None:
    """An EV picked as a buffer load counts its trip energy, not its charging, toward the requirement."""
    network = _buffered_home_network({"reserve": _reserve(["house", "ev"], ["battery"])})

    required = network.elements["reserve"].outputs()["buffer_energy_required"].values
    # 1 kWh of house and the 10 kWh trip fall in the window from boundary 2.
    assert required[2] == pytest.approx(12.0)


def test_buffer_holds_the_trip_energy_in_the_ev_pack() -> None:
    """With the EV also holding the buffer, trip energy already in the pack counts, so nothing extra is held."""
    holding = _buffered_home_network({"reserve": _reserve(["house", "ev"], ["battery", "ev"])})
    home_only = _buffered_home_network({"reserve": _reserve(["house", "ev"], ["battery"])})

    available = holding.elements["reserve"].outputs()["buffer_energy_available"].values
    assert available[2] == pytest.approx(12.0)
    # The pack's 10 kWh covers the trip, so the home battery is not filled for it.
    assert holding.elements["battery"].outputs()[BATTERY_ENERGY_STORED].values[2] == pytest.approx(2.0)
    assert home_only.elements["battery"].outputs()[BATTERY_ENERGY_STORED].values[2] == pytest.approx(12.0)


def test_buffers_over_the_same_batteries_each_hold_their_own_requirement() -> None:
    """A home reserve, a whole-system emergency reserve, and an EV margin hold together over shared batteries."""
    buffers = {
        "home_reserve": _reserve(["house"], ["battery"]),
        "emergency": _reserve(["house", "ev"], ["battery", "ev"], window=4.0),
        "ev_margin": _reserve(["ev"], ["ev"], window=4.0, level=0.2),
    }
    together = _buffered_home_network(buffers, trip_periods=(1, 3))
    margin_only = _buffered_home_network({"ev_margin": buffers["ev_margin"]}, trip_periods=(1, 3))

    def shortfall(network: Network, name: str) -> list[float]:
        return list(network.elements[name].outputs()["buffer_energy_shortfall"].values)

    # The home and emergency reserves are met wherever the plan can still act: the batteries start
    # with 7 kWh against the 14 kWh the emergency reserve asks for now.
    assert shortfall(together, "home_reserve") == pytest.approx([0.0] * 5)
    assert shortfall(together, "emergency") == pytest.approx([7.0, 0.0, 0.0, 0.0, 0.0])
    # The EV margin is the binding one, so it sets the plan the others share.
    np.testing.assert_allclose(
        together.elements["ev:charge"].outputs()["connection_power"].values,
        margin_only.elements["ev:charge"].outputs()["connection_power"].values,
        atol=1e-9,
    )
