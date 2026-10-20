"""Tests for reading how much a meter rose since a point in time."""

import pytest

from conftest import FakeEntityState
from custom_components.haeo.core.data.loader.meter import (
    METER_TOTALS_ATTRIBUTE,
    read_meter_totals,
    rise_since,
    since_window_field,
)


def _state(attributes: dict[str, object]) -> FakeEntityState:
    return FakeEntityState("sensor.meter", "5", attributes)


def test_read_meter_totals_sorts_the_injected_pairs() -> None:
    """Injected totals read as (time, total) pairs, oldest first."""
    state = _state({METER_TOTALS_ATTRIBUTE: [[200.0, 3.0], [100.0, 1.0]]})

    assert read_meter_totals(state) == [(100.0, 1.0), (200.0, 3.0)]


@pytest.mark.parametrize(
    "attributes",
    [
        pytest.param({}, id="no_totals"),
        pytest.param({METER_TOTALS_ATTRIBUTE: "1,2"}, id="not_a_list"),
        pytest.param({METER_TOTALS_ATTRIBUTE: [[100.0]]}, id="not_a_pair"),
        pytest.param({METER_TOTALS_ATTRIBUTE: [[100.0, "x"]]}, id="not_a_number"),
        pytest.param({METER_TOTALS_ATTRIBUTE: [[True, 1.0]]}, id="boolean_time"),
        pytest.param({METER_TOTALS_ATTRIBUTE: [[100.0, float("nan")]]}, id="not_finite"),
    ],
)
def test_read_meter_totals_rejects_states_without_usable_totals(attributes: dict[str, object]) -> None:
    """A state without well-formed totals carries none."""
    assert read_meter_totals(_state(attributes)) is None


def test_read_meter_totals_of_a_missing_state() -> None:
    """A missing state carries no totals."""
    assert read_meter_totals(None) is None


@pytest.mark.parametrize(
    ("since", "expected"),
    [
        pytest.param(150.0, 4.0, id="from_the_total_before"),
        pytest.param(100.0, 4.0, id="from_the_total_at"),
        pytest.param(300.0, 0.0, id="since_the_latest"),
        pytest.param(50.0, None, id="before_the_totals_reach"),
    ],
)
def test_rise_since(since: float, expected: float | None) -> None:
    """The rise runs from the total at or before a time to the latest total."""
    totals = [(100.0, 1.0), (200.0, 3.0), (300.0, 5.0)]

    assert rise_since(totals, since) == expected


def test_a_meter_whose_totals_fell_rose_nothing() -> None:
    """Totals that fell, as a replaced meter's might, rose nothing."""
    assert rise_since([(100.0, 5.0), (200.0, 2.0)], 100.0) == 0.0


def test_since_window_field() -> None:
    """The rise loads beside its field under a derived key."""
    assert since_window_field("energy_meter") == "energy_meter_since_window"
