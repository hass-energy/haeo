"""Tests for the buffer model element's window layout, network wiring, and requirement."""

from collections.abc import Sequence

import numpy as np
import pytest

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_BUFFER,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    BatteryElementConfig,
    BufferElementConfig,
    ConnectionElementConfig,
)
from custom_components.haeo.core.model.elements.buffer import (
    BUFFER_ENERGY_AVAILABLE,
    BUFFER_ENERGY_REQUIRED,
    BUFFER_ENERGY_SHORTFALL,
    BUFFER_STATE_OF_CHARGE,
    Buffer,
    BufferKind,
    window_layout,
    window_peaks,
)
from custom_components.haeo.core.model.output_data import OutputData


@pytest.mark.parametrize(
    ("periods", "window", "block", "last", "fraction"),
    [
        pytest.param([1, 1, 1, 1], 2.0, [0, 0, 1, 1, 2], [2, 3, 4, 4, 4], [0, 0, 0, 0, 0], id="whole_periods"),
        pytest.param(
            [0.5, 1, 1.5, 1],
            1.25,
            [0, 0, 1, 2, 3],
            [1, 2, 2, 4, 4],
            [0.75, 1 / 6, 5 / 6, 0, 0],
            id="window_ends_inside_periods",
        ),
        pytest.param([1, 1], 5.0, [0, 0, 0], [2, 2, 2], [0, 0, 0], id="window_longer_than_horizon"),
        pytest.param([1, 1, 1], 0.5, [0, 2, 4, 6], [0, 1, 2, 3], [0.5, 0.5, 0.5, 0], id="window_shorter_than_periods"),
        pytest.param([1, 1, 1], 0.0, [0, 1, 2, 3], [0, 1, 2, 3], [0, 0, 0, 0], id="zero_window"),
    ],
)
def test_window_layout(
    periods: list[float], window: float, block: list[int], last: list[int], fraction: list[float]
) -> None:
    """Each boundary's window ends at its last boundary plus a fraction of the next period."""
    layout = window_layout(np.asarray(periods, dtype=float), window)

    assert layout.block.tolist() == block
    assert layout.last.tolist() == last
    np.testing.assert_allclose(layout.fraction, fraction)


@pytest.mark.parametrize(
    ("values", "periods", "window", "expected"),
    [
        pytest.param([0, 4, 2, 1], [1, 1, 1], 2.0, [4, 4, 2, 1], id="peak_inside_window"),
        pytest.param([0, 1, 4, 2, 1], [1, 1, 1, 1], 1.25, [1.75, 4, 4, 2, 1], id="end_interpolates_after_last"),
        pytest.param([0, 4, 0, 8], [1, 1, 1], 0.25, [1, 4, 2, 8], id="end_inside_own_period"),
        pytest.param([0, 4, 0, 8], [1, 1, 1], 0.75, [3, 4, 6, 8], id="end_three_quarters_into_own_period"),
        pytest.param([3, 1, 2], [1, 1], 10.0, [3, 2, 2], id="window_past_horizon"),
        pytest.param([3, 1, 2], [1, 1], 0.0, [3, 1, 2], id="zero_window"),
    ],
)
def test_window_peaks(values: list[float], periods: list[float], window: float, expected: list[float]) -> None:
    """The peak covers every boundary in the window and the interpolated value where the window ends."""
    layout = window_layout(np.asarray(periods, dtype=float), window)

    np.testing.assert_allclose(window_peaks(np.asarray(values, dtype=float), layout), expected)


def _fixed_connection(name: str, source: str, target: str, power: Sequence[float]) -> ConnectionElementConfig:
    return {
        "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
        "name": name,
        "source": source,
        "target": target,
        "tags": {0},
        "segments": {
            "power_limit": {"segment_type": "power_limit", "max_power": np.asarray(power, dtype=float), "fixed": True}
        },
    }


def _efficient_connection(name: str, source: str, target: str, efficiency: float) -> ConnectionElementConfig:
    return {
        "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
        "name": name,
        "source": source,
        "target": target,
        "tags": {0},
        "segments": {"efficiency": {"segment_type": "efficiency", "efficiency": efficiency}},
    }


def _network(
    periods: Sequence[float],
    *,
    initial_charge: float = 5.0,
    min_charge: float | None = None,
    max_charge: float | None = None,
    efficiency: float | None = 1.0,
    house: Sequence[float] | None = None,
    solar: Sequence[float] | None = None,
    kind: BufferKind = "reserve",
) -> Network:
    """Return a network with a 10 kWh battery on a passive bus, and a fixed house and solar with a grid when given.

    The battery only discharges for a reserve and only charges for headroom, so
    it cannot cycle energy through its losses or shift grid energy in time. With
    no house or solar nothing flows and its charge stays where it starts. With no
    efficiency the battery has no connection at all.
    """
    network = Network(name="test", periods=np.asarray(periods, dtype=float))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "bus", "is_source": False, "is_sink": False})
    battery: BatteryElementConfig = {
        "element_type": MODEL_ELEMENT_TYPE_BATTERY,
        "name": "battery",
        "capacity": 10.0,
        "initial_charge": initial_charge,
        "charge_limit_cost": 100.0,
    }
    if min_charge is not None:
        battery["min_charge"] = min_charge
    if max_charge is not None:
        battery["max_charge"] = max_charge
    network.add(battery)
    if efficiency is not None:
        name, source, target = (
            ("battery:discharge", "battery", "bus") if kind == "reserve" else ("battery:charge", "bus", "battery")
        )
        network.add(_efficient_connection(name, source, target, efficiency))
    if house is None and solar is None:
        return network
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
    for name, source, target in (("grid:import", "grid", "bus"), ("grid:export", "bus", "grid")):
        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": name,
                "source": source,
                "target": target,
                "tags": {0},
                "segments": {"pricing": {"segment_type": "pricing", "price": 100.0}},
            }
        )
    if house is not None:
        network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "house", "is_source": False, "is_sink": True})
        network.add(_fixed_connection("house:connection", "bus", "house", house))
    if solar is not None:
        network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "solar", "is_source": True, "is_sink": False})
        network.add(_fixed_connection("solar:connection", "solar", "bus", solar))
    return network


def _buffer(
    *,
    kind: BufferKind = "reserve",
    loads: list[str] | None = None,
    generation: list[str] | None = None,
    storage: list[str] | None = None,
    window: float = 1.0,
    level: float | None = None,
    price: float = 1.0,
) -> BufferElementConfig:
    return {
        "element_type": MODEL_ELEMENT_TYPE_BUFFER,
        "name": "buffer",
        "kind": kind,
        "loads": loads or [],
        "generation": generation or [],
        "storage": ["battery"] if storage is None else storage,
        "window": window,
        "level": level,
        "price": price,
    }


def _values(output: OutputData) -> np.ndarray:
    return np.asarray(output.values, dtype=float)


@pytest.mark.parametrize(
    ("config", "error", "match"),
    [
        pytest.param(_buffer(loads=["missing"]), TypeError, "unknown element 'missing'", id="unknown_load"),
        pytest.param(_buffer(generation=["missing"]), TypeError, "unknown element 'missing'", id="unknown_generation"),
        pytest.param(
            _buffer(storage=["missing"]), TypeError, "'missing', which is not a battery", id="unknown_battery"
        ),
        pytest.param(
            _buffer(storage=["house"]), TypeError, "'house', which is not a battery", id="storage_not_a_battery"
        ),
    ],
)
def test_buffer_rejects_references_it_cannot_resolve(
    config: BufferElementConfig, error: type[Exception], match: str
) -> None:
    """A buffer covers network elements and is held by batteries."""
    network = _network([1.0, 1.0], house=[1.0, 1.0])

    with pytest.raises(error, match=match):
        network.add(config)


@pytest.mark.parametrize(
    ("periods", "window", "house", "efficiency"),
    [
        pytest.param([1, 1, 1, 1], 1.25, [1, 3, 2, 4], 1.0, id="end_a_quarter_into_next_period"),
        pytest.param([1, 1, 1, 1], 1.75, [1, 3, 2, 4], 1.0, id="end_three_quarters_into_next_period"),
        pytest.param([1, 1, 1, 1], 0.25, [1, 3, 2, 4], 1.0, id="end_a_quarter_into_own_period"),
        pytest.param([1, 1, 1, 1], 0.75, [1, 3, 2, 4], 1.0, id="end_three_quarters_into_own_period"),
        pytest.param([0.5, 1, 1.5, 1], 1.25, [2, 1, 3, 1], 1.0, id="uneven_periods"),
        pytest.param([1, 1, 1, 1], 1.25, [1, 3, 2, 4], 0.8, id="discharge_losses"),
    ],
)
def test_empty_reserve_shortfall_matches_required(
    periods: list[float], window: float, house: list[float], efficiency: float
) -> None:
    """With an empty battery the whole requirement is shortfall, and the LP and outputs agree on it.

    The house's running demand only rises, so the peak of each window is where
    it ends, interpolated between the boundaries around it, and the batteries
    must store it before discharge losses.
    """
    network = _network(periods, initial_charge=0.0, efficiency=efficiency, house=house)
    network.add(_buffer(loads=["house"], window=window))

    network.optimize()
    outputs = network.elements["buffer"].outputs()

    times = np.concatenate(([0.0], np.cumsum(periods)))
    demand = np.concatenate(([0.0], np.cumsum(np.asarray(house) * np.asarray(periods))))
    expected = (np.interp(times + window, times, demand) - demand) / efficiency
    np.testing.assert_allclose(_values(outputs[BUFFER_ENERGY_REQUIRED]), expected, atol=1e-9)
    np.testing.assert_allclose(_values(outputs[BUFFER_ENERGY_SHORTFALL]), expected, atol=1e-9)
    np.testing.assert_allclose(_values(outputs[BUFFER_ENERGY_AVAILABLE]), 0.0, atol=1e-9)


def test_first_period_consumption_counts_toward_the_first_boundary() -> None:
    """A load planned in the first period falls in the first boundary's window, so it is held and priced.

    The battery starts with 2 kWh for a house that uses 3 kWh in the first hour,
    so the first boundary falls 1 kWh short, priced for the first period.
    """
    network = _network([1.0, 1.0], initial_charge=2.0, house=[3.0, 0.0])
    network.add(_buffer(loads=["house"], window=1.0, price=0.5))

    network.optimize()
    outputs = network.elements["buffer"].outputs()

    np.testing.assert_allclose(_values(outputs[BUFFER_ENERGY_REQUIRED]), [3.0, 0.0, 0.0], atol=1e-9)
    np.testing.assert_allclose(_values(outputs[BUFFER_ENERGY_SHORTFALL]), [1.0, 0.0, 0.0], atol=1e-9)
    buffer = network.elements["buffer"]
    assert sum(buffer.extract_values(buffer.cost())) == pytest.approx(0.5 * 1.0 * 1.0)


@pytest.mark.parametrize(
    ("kind", "min_charge", "max_charge", "level", "line", "shortfall"),
    [
        pytest.param("reserve", 2.0, None, 0.3, 0.3, 0.0, id="reserve_level_above_min"),
        pytest.param("reserve", 2.0, None, 0.1, 0.2, 0.0, id="reserve_level_below_min_uses_min"),
        pytest.param("reserve", 2.0, None, None, 0.2, 0.0, id="reserve_unset_level_uses_min"),
        pytest.param("reserve", None, None, None, 0.0, 0.0, id="reserve_unset_level_and_min_uses_empty"),
        pytest.param("reserve", 2.0, None, 0.6, 0.6, 1.0, id="reserve_level_above_charge_falls_short"),
        pytest.param("headroom", None, 8.0, 0.7, 0.7, 0.0, id="headroom_level_below_max"),
        pytest.param("headroom", None, 8.0, 0.9, 0.8, 0.0, id="headroom_level_above_max_uses_max"),
        pytest.param("headroom", None, 8.0, None, 0.8, 0.0, id="headroom_unset_level_uses_max"),
        pytest.param("headroom", None, None, None, 1.0, 0.0, id="headroom_unset_level_and_max_uses_full"),
        pytest.param("headroom", None, 8.0, 0.4, 0.4, 1.0, id="headroom_level_below_charge_falls_short"),
    ],
)
def test_buffer_measures_from_its_level_within_the_battery_limits(
    kind: BufferKind,
    min_charge: float | None,
    max_charge: float | None,
    level: float | None,
    line: float,
    shortfall: float,
) -> None:
    """A buffer with nothing to cover sits at its level, kept inside the battery's min and max charge.

    The battery holds 5 kWh of 10 throughout, so a reserve above it or headroom below it falls short.
    """
    network = _network([1.0, 1.0], min_charge=min_charge, max_charge=max_charge, kind=kind)
    network.add(_buffer(kind=kind, level=level))

    network.optimize()
    outputs = network.elements["buffer"].outputs()

    soc = outputs[BUFFER_STATE_OF_CHARGE]
    assert soc.direction == ("+" if kind == "reserve" else "-")
    np.testing.assert_allclose(_values(soc), line)
    np.testing.assert_allclose(_values(outputs[BUFFER_ENERGY_REQUIRED]), 0.0, atol=1e-9)
    np.testing.assert_allclose(_values(outputs[BUFFER_ENERGY_SHORTFALL]), [shortfall] * 3, atol=1e-9)


@pytest.mark.parametrize("kind", ["reserve", "headroom"])
@pytest.mark.parametrize("efficiency", [1.0, 0.8, 0.5])
def test_shortfall_costs_the_stored_energy_past_the_level(kind: BufferKind, efficiency: float) -> None:
    """A shortfall costs its price per stored kWh per hour, whatever the battery's efficiency.

    The battery holds 5 kWh of 10 and the buffer's level is 3 kWh past it, which
    is what a battery partition charged for holding the battery past its limit.
    The first boundary is held for the first period as well, a cost the plan
    cannot change since the battery's charge there is fixed.
    """
    network = _network([1.0, 0.5, 2.0], efficiency=efficiency, kind=kind)
    network.add(_buffer(kind=kind, level=0.8 if kind == "reserve" else 0.2, price=0.5))

    cost = network.optimize()

    assert cost == pytest.approx(0.5 * 3.0 * (1.0 + 3.5))


@pytest.mark.parametrize(
    ("kind", "level", "line"),
    [
        pytest.param("reserve", 0.2, [0.3, 0.3, 0.2], id="reserve_line_above_level"),
        pytest.param("headroom", 0.8, [0.7, 0.7, 0.8], id="headroom_line_below_level"),
    ],
)
def test_state_of_charge_line_adds_the_requirement_to_the_level(
    kind: BufferKind, level: float, line: list[float]
) -> None:
    """The line is the level plus the energy a reserve needs, or less the space headroom needs.

    The house uses 1 kW and the solar makes 1 kW, so each needs 1 kWh over a one hour window.
    """
    network = _network([1.0, 1.0], house=[1.0, 1.0], solar=[1.0, 1.0], kind=kind)
    network.add(
        _buffer(
            kind=kind,
            loads=["house"] if kind == "reserve" else [],
            generation=["solar"] if kind == "headroom" else [],
            level=level,
        )
    )

    network.optimize()
    outputs = network.elements["buffer"].outputs()

    np.testing.assert_allclose(_values(outputs[BUFFER_STATE_OF_CHARGE]), line, atol=1e-9)


@pytest.mark.parametrize(
    ("kind", "spare", "spare_efficiency", "required"),
    [
        pytest.param("reserve", "out", 0.8, [2.0, 2.0, 0.0], id="reserve_takes_the_lower_outbound"),
        pytest.param("reserve", "out", 0.25, [4.0, 4.0, 0.0], id="reserve_takes_the_lower_outbound_spare"),
        pytest.param("reserve", "in", 0.25, [2.0, 2.0, 0.0], id="reserve_ignores_inbound"),
        pytest.param("headroom", "in", 0.25, [0.25, 0.25, 0.0], id="headroom_takes_the_lower_inbound"),
        pytest.param("headroom", "out", 0.25, [0.5, 0.5, 0.0], id="headroom_ignores_outbound"),
    ],
)
def test_storage_counts_the_lowest_efficiency_of_its_connections_for_its_kind(
    kind: BufferKind, spare: str, spare_efficiency: float, required: list[float]
) -> None:
    """A battery holds the buffer through the worst of the connections a reserve leaves or headroom enters by.

    The battery's own connection is 50% efficient and a second connection runs to
    or from a passive node. The house uses, or the solar makes, 1 kW over a one
    hour window, as stored energy before the reserve's losses or after headroom's.
    """
    network = _network(
        [1.0, 1.0],
        efficiency=0.5,
        house=[1.0, 1.0] if kind == "reserve" else None,
        solar=[1.0, 1.0] if kind == "headroom" else None,
        kind=kind,
    )
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "spare", "is_source": False, "is_sink": False})
    source, target = ("battery", "spare") if spare == "out" else ("spare", "battery")
    network.add(_efficient_connection("battery:spare", source, target, spare_efficiency))
    network.add(
        _buffer(
            kind=kind,
            loads=["house"] if kind == "reserve" else [],
            generation=["solar"] if kind == "headroom" else [],
        )
    )

    network.optimize()
    outputs = network.elements["buffer"].outputs()

    np.testing.assert_allclose(_values(outputs[BUFFER_ENERGY_REQUIRED]), required, atol=1e-9)


def test_storage_without_connections_counts_without_losses() -> None:
    """A battery with no connections still holds the buffer, at face value."""
    network = _network([1.0, 1.0], efficiency=None, house=[1.0, 1.0])
    network.add(_buffer(loads=["house"]))

    network.optimize()
    outputs = network.elements["buffer"].outputs()

    np.testing.assert_allclose(_values(outputs[BUFFER_ENERGY_REQUIRED]), [1.0, 1.0, 0.0], atol=1e-9)


@pytest.mark.parametrize(
    ("extra_limit", "required"),
    [
        pytest.param(5.0, [6.0, 6.0, 0.0], id="limited_connection_adds"),
        pytest.param(None, [1.0, 1.0, 0.0], id="unlimited_connection_adds_nothing"),
    ],
)
def test_generation_counts_the_limits_on_every_connection_out_of_it(
    extra_limit: float | None, required: list[float]
) -> None:
    """Headroom counts the limits on every connection out of a generator.

    The solar makes 1 kW through its own connection and a second connection out of
    it may carry 5 kW more, or have no limit.
    """
    network = _network([1.0, 1.0], house=[0.0, 0.0], solar=[1.0, 1.0], kind="headroom")
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "solar:extra",
            "source": "solar",
            "target": "bus",
            "tags": {0},
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power": None if extra_limit is None else np.full(2, extra_limit),
                }
            },
        }
    )
    network.add(_buffer(kind="headroom", generation=["solar"]))

    network.optimize()
    outputs = network.elements["buffer"].outputs()

    np.testing.assert_allclose(_values(outputs[BUFFER_ENERGY_REQUIRED]), required, atol=1e-9)


def test_required_energy_is_computed_once_per_solution() -> None:
    """Outputs read one required energy array per solution, and a new solve computes it afresh."""
    network = _network([1.0, 1.0], house=[1.0, 1.0])
    network.add(_buffer(loads=["house"]))
    buffer = network.elements["buffer"]
    assert isinstance(buffer, Buffer)
    network.optimize()

    first = buffer._required_values()
    assert buffer._required_values() is first

    buffer.window = 2.0
    network.optimize()
    second = buffer._required_values()

    assert second is not first
    np.testing.assert_allclose(first, [1.0, 1.0, 0.0], atol=1e-9)
    np.testing.assert_allclose(second, [2.0, 1.0, 0.0], atol=1e-9)
