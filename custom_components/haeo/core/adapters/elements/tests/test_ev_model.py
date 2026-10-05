"""Tests for EV element model mapping and trip optimization behavior."""

from typing import Any

import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.ev import (
    DEFAULT_PUBLIC_CHARGING_PRICE,
    EV_DEVICE_EV,
    EV_ENERGY_STORED,
    EV_POWER_ACTIVE,
    EV_POWER_CHARGE,
    EV_POWER_DISCHARGE,
    EV_RESERVE_SHORTFALL,
    EV_STATE_OF_CHARGE,
    EV_TRIP_ENERGY_DELIVERED,
    EV_TRIP_ENERGY_SHORTFALL,
    adapter,
)
from custom_components.haeo.core.data.loader.calendar_resolver import CalendarBoundaryData
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.battery import BATTERY_ENERGY_STORED
from custom_components.haeo.core.model.elements.deferrable_load import (
    DEFERRABLE_LOAD_ENERGY_DELIVERED,
    DEFERRABLE_LOAD_ENERGY_SHORTFALL,
)
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.ev import EvConfigData


def _boundary_data(
    presence: list[float],
    value_edge_start: list[float],
    value_edge_end: list[float],
) -> CalendarBoundaryData:
    """Build calendar boundary data with a derived value_span.

    A window's value spans the boundaries from its start edge up to, but not
    including, its end edge, matching the calendar fuser.
    """
    span = np.cumsum(value_edge_start) - np.cumsum(value_edge_end)
    return CalendarBoundaryData(
        presence=np.array(presence, dtype=np.float64),
        value_span=np.asarray(span, dtype=np.float64),
        value_edge_start=np.array(value_edge_start, dtype=np.float64),
        value_edge_end=np.array(value_edge_end, dtype=np.float64),
    )


def _ev_config(**overrides: Any) -> EvConfigData:
    """Build an EV config with sensible defaults, applying overrides."""
    config: dict[str, Any] = {
        "element_type": ElementType.EV,
        "name": "ev",
        "connection": as_connection_target("home"),
        "vehicle": {
            "capacity": np.array([50.0] * 5),
            "energy_per_distance": 0.2,
            "current_soc": 0.10,
        },
        "charging": {
            "max_charge_rate": 10.0,
        },
        "power_limits": {},
        "efficiency": {},
    }
    config.update(overrides)
    return config  # type: ignore[return-value]  # constructed to match EvConfigData


def _elements_by_name(config: EvConfigData) -> dict[str, dict[str, Any]]:
    return {element["name"]: dict(element) for element in adapter.model_elements(config)}


# --- model_elements structure ---


def test_model_elements_structure() -> None:
    """The adapter creates the five expected model elements."""
    elements = _elements_by_name(_ev_config())

    assert set(elements) == {
        "ev",
        "ev:charge",
        "ev:discharge",
        "ev:trip",
        "ev:trip_connection",
    }
    assert elements["ev"]["element_type"] == "battery"
    assert elements["ev"]["initial_charge"] == pytest.approx(5.0)  # SOC ratio 0.10 of 50 kWh
    assert elements["ev:charge"]["source"] == "home"
    assert elements["ev:charge"]["target"] == "ev"
    assert elements["ev:discharge"]["source"] == "ev"
    assert elements["ev:discharge"]["target"] == "home"
    assert elements["ev:trip"]["element_type"] == "deferrable_load"
    assert elements["ev:trip_connection"]["source"] == "ev"
    assert elements["ev:trip_connection"]["target"] == "ev:trip"


def test_no_trip_config_yields_inert_trip_load() -> None:
    """Without trip data the trip load requires nothing and nothing can flow."""
    elements = _elements_by_name(_ev_config())

    trip = elements["ev:trip"]
    assert trip["in_window"] == 0.0
    assert trip["requirement"] == 0.0
    assert trip["initial_energy"] == 0.0
    assert "overage_price" not in trip
    assert elements["ev:trip_connection"]["segments"]["power_limit"]["max_power"] == 0.0


def test_default_public_price_applies_when_unconfigured() -> None:
    """The trip deficit is always priced, defaulting to the high price."""
    elements = _elements_by_name(_ev_config())

    assert elements["ev:trip"]["deficit_price"] == DEFAULT_PUBLIC_CHARGING_PRICE


def test_configured_public_price_is_used() -> None:
    """A configured public charging price becomes the deficit price."""
    elements = _elements_by_name(_ev_config(public_charging={"public_charging_price": 0.6}))

    assert elements["ev:trip"]["deficit_price"] == pytest.approx(0.6)


def test_interval_public_price_extends_to_boundaries() -> None:
    """A per-interval public price is extended to the trip load's boundaries."""
    elements = _elements_by_name(_ev_config(public_charging={"public_charging_price": np.array([0.4, 0.5, 0.6, 0.7])}))

    np.testing.assert_allclose(elements["ev:trip"]["deficit_price"], [0.4, 0.5, 0.6, 0.7, 0.7])


@pytest.mark.parametrize(
    ("public_charging", "trip_extra", "expected_deficit_price", "expected_reserve_price"),
    [
        pytest.param({"public_charging_price": -2.0}, {}, 0.0, 0.0, id="negative_public_price"),
        pytest.param(
            {"public_charging_price": np.array([-1.0, 0.5, -0.5, 0.7])},
            {},
            [0.0, 0.5, 0.0, 0.7, 0.7],
            [0.0, 0.5, 0.0, 0.7, 0.7],
            id="partly_negative_public_series",
        ),
        pytest.param(
            {"public_charging_price": 0.6},
            {"reserve_price": -3.0},
            0.6,
            0.0,
            id="negative_reserve_price",
        ),
    ],
)
def test_negative_penalty_prices_are_clamped_to_zero(
    public_charging: dict[str, Any],
    trip_extra: dict[str, Any],
    expected_deficit_price: float | list[float],
    expected_reserve_price: float | list[float],
) -> None:
    """Negative public or reserve prices from an entity cannot pay the optimizer to miss a trip."""
    elements = _elements_by_name(_ev_config(trip=_reserve_trip(**trip_extra), public_charging=public_charging))

    np.testing.assert_allclose(elements["ev:trip"]["deficit_price"], expected_deficit_price)
    np.testing.assert_allclose(elements["ev"]["reserve_price"], expected_reserve_price)


def test_calendar_drives_trip_arrays_and_masks() -> None:
    """Calendar presence and edges become trip windows, requirement, and masks."""
    config = _ev_config(
        trip={
            "trip_calendar": _boundary_data(
                presence=[0.0, 0.0, 1.0, 0.0, 0.0],
                value_edge_start=[0.0, 0.0, 30.0, 0.0, 0.0],
                value_edge_end=[0.0, 0.0, 0.0, 30.0, 0.0],
            ),
        },
    )
    elements = _elements_by_name(config)

    trip = elements["ev:trip"]
    np.testing.assert_allclose(trip["in_window"], [0.0, 0.0, 1.0, 0.0])
    np.testing.assert_allclose(trip["window_start"], [0.0, 0.0, 1.0, 0.0, 0.0])
    np.testing.assert_allclose(trip["requirement"], [0.0, 0.0, 0.0, 6.0, 0.0])  # 30 km * 0.2 kWh/km
    assert "overage_price" not in trip

    # Home charging masked off while away (period 2), trip flow open only then.
    home_charge_limit = elements["ev:charge"]["segments"]["power_limit"]["max_power"]
    np.testing.assert_allclose(home_charge_limit, [10.0, 10.0, 0.0, 10.0])
    trip_limit = elements["ev:trip_connection"]["segments"]["power_limit"]["max_power"]
    np.testing.assert_allclose(np.asarray(trip_limit) > 0, [False, False, True, False])


def test_live_connected_sensor_pins_first_interval() -> None:
    """The live sensor overrides the calendar for the current interval only."""
    config = _ev_config(
        trip={
            "trip_calendar": _boundary_data(
                presence=[0.0, 0.0, 1.0, 0.0, 0.0],
                value_edge_start=[0.0, 0.0, 30.0, 0.0, 0.0],
                value_edge_end=[0.0, 0.0, 0.0, 30.0, 0.0],
            ),
            "connected": 0.0,
        },
    )
    elements = _elements_by_name(config)

    home_charge_limit = elements["ev:charge"]["segments"]["power_limit"]["max_power"]
    np.testing.assert_allclose(home_charge_limit, [0.0, 10.0, 0.0, 10.0])


def test_calendar_governs_current_interval_without_plugged_in_sensor() -> None:
    """With only a calendar, a trip window open now keeps the car away now."""
    config = _ev_config(
        trip={
            "trip_calendar": _boundary_data(
                presence=[1.0, 1.0, 0.0, 0.0, 0.0],
                value_edge_start=[30.0, 0.0, 0.0, 0.0, 0.0],
                value_edge_end=[0.0, 0.0, 30.0, 0.0, 0.0],
            ),
        },
    )
    elements = _elements_by_name(config)

    home_charge_limit = elements["ev:charge"]["segments"]["power_limit"]["max_power"]
    np.testing.assert_allclose(home_charge_limit, [0.0, 0.0, 10.0, 10.0])


def test_odometer_progress_reduces_trip_requirement() -> None:
    """While away, distance already driven becomes trip battery initial charge."""
    config = _ev_config(
        trip={
            "trip_calendar": _boundary_data(
                presence=[1.0, 0.0, 0.0, 0.0, 0.0],
                value_edge_start=[30.0, 0.0, 0.0, 0.0, 0.0],
                value_edge_end=[0.0, 30.0, 0.0, 0.0, 0.0],
            ),
            "connected": 0.0,
            "odometer": 10_050.0,
            "odometer_at_disconnect": 10_040.0,
        },
    )
    elements = _elements_by_name(config)

    # 10 km driven * 0.2 kWh/km = 2 kWh already consumed
    assert elements["ev:trip"]["initial_energy"] == pytest.approx(2.0)


def test_odometer_progress_not_credited_outside_trip_window() -> None:
    """Distance from a finished trip does not cover a future trip while unplugged."""
    config = _ev_config(
        trip={
            "trip_calendar": _boundary_data(
                presence=[0.0, 0.0, 1.0, 0.0, 0.0],
                value_edge_start=[0.0, 0.0, 50.0, 0.0, 0.0],
                value_edge_end=[0.0, 0.0, 0.0, 50.0, 0.0],
            ),
            "connected": 0.0,
            "odometer": 10_300.0,
            "odometer_at_disconnect": 10_000.0,
        },
    )
    elements = _elements_by_name(config)

    assert elements["ev:trip"]["initial_energy"] == 0.0


def test_odometer_progress_credits_only_the_open_trip_window() -> None:
    """Distance driven beyond the open trip completes it without reaching later trips."""
    config = _ev_config(
        trip={
            "trip_calendar": _boundary_data(
                presence=[1.0, 0.0, 0.0, 1.0, 0.0],
                value_edge_start=[30.0, 0.0, 0.0, 50.0, 0.0],
                value_edge_end=[0.0, 30.0, 0.0, 0.0, 50.0],
            ),
            "connected": 0.0,
            "odometer": 10_100.0,
            "odometer_at_disconnect": 10_000.0,
        },
    )
    elements = _elements_by_name(config)

    # The full 100 km seeds only the open window; the model treats the
    # overshoot as sunk, so the later 50 km trip is still fully due.
    assert elements["ev:trip"]["initial_energy"] == pytest.approx(20.0)


def test_odometer_progress_ignored_while_connected() -> None:
    """Stale odometer readings do not credit the trip battery when home."""
    config = _ev_config(
        trip={
            "trip_calendar": _boundary_data(
                presence=[0.0, 0.0, 1.0, 0.0, 0.0],
                value_edge_start=[0.0, 0.0, 30.0, 0.0, 0.0],
                value_edge_end=[0.0, 0.0, 0.0, 30.0, 0.0],
            ),
            "connected": 1.0,
            "odometer": 10_050.0,
            "odometer_at_disconnect": 10_000.0,
        },
    )
    elements = _elements_by_name(config)

    assert elements["ev:trip"]["initial_energy"] == 0.0


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
    config = _ev_config(
        trip={
            "trip_calendar": _boundary_data(
                presence=[0.0, 0.0, 1.0, 0.0, 0.0],
                value_edge_start=[0.0, 0.0, 30.0, 0.0, 0.0],
                value_edge_end=[0.0, 0.0, 0.0, 30.0, 0.0],
            ),
        },
    )
    network = _solve_ev_network(config, grid_price=[0.1, 0.5, 0.5, 0.5])

    trip_delivered = network.elements["ev:trip"].outputs()[DEFERRABLE_LOAD_ENERGY_DELIVERED].values
    assert trip_delivered[3] == pytest.approx(6.0, abs=1e-6)

    # The 1 kWh top-up (5 kWh initial vs 6 kWh trip) buys in the cheap period.
    ev_stored = network.elements["ev"].outputs()[BATTERY_ENERGY_STORED].values
    assert ev_stored[1] == pytest.approx(6.0, abs=1e-6)


def test_shortfall_is_priced_at_the_public_price() -> None:
    """When home charging cannot cover the trip, the shortfall is priced."""
    config = _ev_config(
        charging={"max_charge_rate": 2.0},
        trip={
            "trip_calendar": _boundary_data(
                presence=[0.0, 0.0, 1.0, 0.0, 0.0],
                value_edge_start=[0.0, 0.0, 100.0, 0.0, 0.0],
                value_edge_end=[0.0, 0.0, 0.0, 100.0, 0.0],
            ),
        },
        public_charging={"public_charging_price": 0.8},
    )
    # Trip needs 20 kWh; pack holds 5 + at most 4 charged before departure.
    network = _solve_ev_network(config, grid_price=[0.1, 0.1, 0.1, 0.1])

    trip_outputs = network.elements["ev:trip"].outputs()
    delivered = trip_outputs[DEFERRABLE_LOAD_ENERGY_DELIVERED].values
    shortfall = trip_outputs[DEFERRABLE_LOAD_ENERGY_SHORTFALL].values
    assert delivered[3] == pytest.approx(9.0, abs=1e-6)
    assert shortfall[3] == pytest.approx(11.0, abs=1e-6)


# --- Outputs mapping ---


def test_outputs_mapping_from_solved_network() -> None:
    """Adapter outputs map solved model values to EV output names."""
    config = _ev_config(
        trip={
            "trip_calendar": _boundary_data(
                presence=[0.0, 0.0, 1.0, 0.0, 0.0],
                value_edge_start=[0.0, 0.0, 30.0, 0.0, 0.0],
                value_edge_end=[0.0, 0.0, 0.0, 30.0, 0.0],
            ),
        },
    )
    network = _solve_ev_network(config, grid_price=[0.1, 0.5, 0.5, 0.5])
    model_outputs = {name: element.outputs() for name, element in network.elements.items()}

    outputs = adapter.outputs("ev", model_outputs, config=config)[EV_DEVICE_EV]

    assert set(outputs) >= {
        EV_POWER_CHARGE,
        EV_POWER_DISCHARGE,
        EV_POWER_ACTIVE,
        EV_STATE_OF_CHARGE,
        EV_ENERGY_STORED,
        EV_TRIP_ENERGY_DELIVERED,
        EV_TRIP_ENERGY_SHORTFALL,
    }

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


# --- Telemetry robustness ---


def test_odometer_overshoot_beyond_trip_stays_feasible() -> None:
    """A car that drove further than the scheduled trip must still solve."""
    config = _ev_config(
        trip={
            "trip_calendar": _boundary_data(
                presence=[1.0, 0.0, 0.0, 0.0, 0.0],
                value_edge_start=[30.0, 0.0, 0.0, 0.0, 0.0],
                value_edge_end=[0.0, 30.0, 0.0, 0.0, 0.0],
            ),
            "connected": 0.0,
            "odometer": 10_100.0,
            "odometer_at_disconnect": 10_000.0,  # 100 km driven on a 30 km trip
        },
    )
    elements = _elements_by_name(config)
    assert elements["ev:trip"]["initial_energy"] == pytest.approx(20.0)

    network = _solve_ev_network(config, grid_price=[0.1, 0.1, 0.1, 0.1])

    trip_outputs = network.elements["ev:trip"].outputs()
    # The overshoot is sunk: no shortfall, and no new trip energy drawn.
    np.testing.assert_allclose(trip_outputs[DEFERRABLE_LOAD_ENERGY_SHORTFALL].values, [0.0] * 5)
    assert trip_outputs[DEFERRABLE_LOAD_ENERGY_DELIVERED].values[1] == pytest.approx(20.0)
    assert network.elements["ev:trip_connection"].outputs()["connection_power"].values[0] == pytest.approx(0.0)


def _open_trip_config(**trip: Any) -> EvConfigData:
    """Build a config with a 30 km (6 kWh) trip open from before the horizon to boundary 2."""
    return _ev_config(
        trip={
            "trip_calendar": _boundary_data(
                presence=[1.0, 1.0, 0.0, 0.0, 0.0],
                value_edge_start=[30.0, 0.0, 0.0, 0.0, 0.0],
                value_edge_end=[0.0, 0.0, 30.0, 0.0, 0.0],
            ),
            **trip,
        },
    )


def test_odometer_under_target_leaves_the_remainder_due() -> None:
    """Driving less than planned so far leaves the rest of the trip due at its end."""
    config = _open_trip_config(connected=0.0, odometer=10_010.0, odometer_at_disconnect=10_000.0)

    network = _solve_ev_network(config, grid_price=[0.1, 0.1, 0.1, 0.1])

    trip_outputs = network.elements["ev:trip"].outputs()
    delivered = trip_outputs[DEFERRABLE_LOAD_ENERGY_DELIVERED].values
    assert delivered[0] == pytest.approx(2.0)
    assert delivered[2] == pytest.approx(6.0)
    # Pack held 5 kWh; the remaining 4 kWh of the trip comes from it.
    assert network.elements["ev"].outputs()[BATTERY_ENERGY_STORED].values[2] == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("odometer", "odometer_at_disconnect"),
    [
        pytest.param(9_000.0, 10_000.0, id="negative_delta"),
        pytest.param(float("nan"), 10_000.0, id="nan_reading"),
        pytest.param(float("inf"), 10_000.0, id="infinite_reading"),
        pytest.param(None, 10_000.0, id="missing_odometer"),
        pytest.param(10_050.0, None, id="missing_disconnect_reading"),
    ],
)
def test_odometer_garbage_credits_nothing(odometer: float | None, odometer_at_disconnect: float | None) -> None:
    """Reset, stale, or missing odometer readings credit no trip energy."""
    config = _open_trip_config(connected=0.0, odometer=odometer, odometer_at_disconnect=odometer_at_disconnect)

    assert _elements_by_name(config)["ev:trip"]["initial_energy"] == 0.0


def test_plugged_in_during_open_trip_ends_the_trip() -> None:
    """A car plugged in while the calendar says a trip is open is home: no trip energy or public charging."""
    config = _open_trip_config(
        connected=1.0,
        reserve_soc=0.2,
        odometer=10_010.0,
        odometer_at_disconnect=10_000.0,
    )
    elements = _elements_by_name(config)

    trip = elements["ev:trip"]
    np.testing.assert_allclose(trip["in_window"], [0.0, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(trip["requirement"], [0.0] * 5)
    assert trip["initial_energy"] == 0.0
    # Home for the rest of the scheduled trip, and its end is not reserve checked.
    np.testing.assert_allclose(elements["ev:charge"]["segments"]["power_limit"]["max_power"], [10.0] * 4)
    np.testing.assert_allclose(elements["ev"]["reserve_mask"], [0.0] * 5)

    network = _solve_ev_network(config, grid_price=[0.1, 0.1, 0.1, 0.1])

    trip_outputs = network.elements["ev:trip"].outputs()
    np.testing.assert_allclose(trip_outputs[DEFERRABLE_LOAD_ENERGY_SHORTFALL].values, [0.0] * 5)
    np.testing.assert_allclose(trip_outputs[DEFERRABLE_LOAD_ENERGY_DELIVERED].values, [0.0] * 5)


def test_plugged_in_keeps_later_trips() -> None:
    """Ending the open trip leaves a touching later trip in place."""
    config = _ev_config(
        trip={
            "trip_calendar": _boundary_data(
                presence=[1.0, 1.0, 1.0, 0.0, 0.0],
                value_edge_start=[30.0, 20.0, 0.0, 0.0, 0.0],
                value_edge_end=[0.0, 30.0, 0.0, 20.0, 0.0],
            ),
            "connected": 1.0,
        },
    )
    elements = _elements_by_name(config)

    trip = elements["ev:trip"]
    np.testing.assert_allclose(trip["in_window"], [0.0, 1.0, 1.0, 0.0])
    np.testing.assert_allclose(trip["window_start"], [0.0, 1.0, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(trip["requirement"], [0.0, 0.0, 0.0, 4.0, 0.0])
    np.testing.assert_allclose(elements["ev:charge"]["segments"]["power_limit"]["max_power"], [10.0, 0.0, 0.0, 10.0])


def test_glitched_soc_sensor_is_clamped() -> None:
    """A SOC reading above 100% cannot make the pack overfull."""
    config = _ev_config()
    config["vehicle"]["current_soc"] = 2.5  # 250% from a glitched sensor

    elements = _elements_by_name(config)

    assert elements["ev"]["initial_charge"] == pytest.approx(50.0)  # clamped to capacity


# --- Reserve demand pricing ---


def _reserve_trip(**extra: Any) -> dict[str, Any]:
    """Trip config with a calendar and a 20% reserve."""
    return {
        "trip_calendar": _boundary_data(
            presence=[0.0, 0.0, 1.0, 0.0, 0.0],
            value_edge_start=[0.0, 0.0, 30.0, 0.0, 0.0],
            value_edge_end=[0.0, 0.0, 0.0, 30.0, 0.0],
        ),
        "reserve_soc": 0.2,
        **extra,
    }


def test_reserve_config_masks_trip_window_ends() -> None:
    """The reserve applies at trip end boundaries with the pack-scaled level."""
    config = _ev_config(trip=_reserve_trip(reserve_price=0.5))
    elements = _elements_by_name(config)

    battery = elements["ev"]
    np.testing.assert_allclose(battery["reserve_level"], [10.0] * 5)  # 20% of 50 kWh
    np.testing.assert_allclose(battery["reserve_mask"], [0.0, 0.0, 0.0, 1.0, 0.0])
    assert battery["reserve_price"] == pytest.approx(0.5)


def test_reserve_price_defaults_to_public_price() -> None:
    """Without an explicit price the public charging price applies."""
    config = _ev_config(trip=_reserve_trip(), public_charging={"public_charging_price": 0.7})
    elements = _elements_by_name(config)

    assert elements["ev"]["reserve_price"] == pytest.approx(0.7)


def test_reserve_drives_extra_precharge() -> None:
    """With a reserve, the optimizer charges for the trip plus the buffer."""
    config = _ev_config(trip=_reserve_trip(reserve_price=2.0))
    network = _solve_ev_network(config, grid_price=[0.1, 0.5, 0.5, 0.5])

    # Pack ends the trip at the 10 kWh reserve instead of 0.
    ev_stored = network.elements["ev"].outputs()[BATTERY_ENERGY_STORED].values
    assert ev_stored[3] == pytest.approx(10.0, abs=1e-6)

    outputs = adapter.outputs("ev", {n: e.outputs() for n, e in network.elements.items()}, config=config)[EV_DEVICE_EV]
    assert outputs[EV_RESERVE_SHORTFALL].values[3] == pytest.approx(0.0, abs=1e-6)


def test_reserve_shortfall_reported_when_unavoidable() -> None:
    """When the buffer cannot be met, the shortfall sensor reports the dip."""
    config = _ev_config(
        charging={"max_charge_rate": 0.5},  # can only add 1 kWh before departure
        trip=_reserve_trip(reserve_price=0.01),
        public_charging={"public_charging_price": 10.0},
    )
    network = _solve_ev_network(config, grid_price=[0.1, 0.1, 0.1, 0.1])

    outputs = adapter.outputs("ev", {n: e.outputs() for n, e in network.elements.items()}, config=config)[EV_DEVICE_EV]
    # Pack holds at most 6 kWh at departure; the trip drains it toward zero,
    # so the 10 kWh reserve is missed at the trip end boundary.
    assert outputs[EV_RESERVE_SHORTFALL].values[3] > 0.0


def test_no_reserve_means_no_reserve_output() -> None:
    """Without reserve configuration the EV exposes no reserve sensor."""
    config = _ev_config(
        trip={
            "trip_calendar": _boundary_data(
                presence=[0.0, 0.0, 1.0, 0.0, 0.0],
                value_edge_start=[0.0, 0.0, 30.0, 0.0, 0.0],
                value_edge_end=[0.0, 0.0, 0.0, 30.0, 0.0],
            ),
        },
    )
    network = _solve_ev_network(config, grid_price=[0.1, 0.5, 0.5, 0.5])

    outputs = adapter.outputs("ev", {n: e.outputs() for n, e in network.elements.items()}, config=config)[EV_DEVICE_EV]
    assert EV_RESERVE_SHORTFALL not in outputs
