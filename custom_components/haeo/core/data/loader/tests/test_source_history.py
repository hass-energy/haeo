"""Tests for reading source history out of injected state attributes."""

import pytest

from conftest import FakeEntityState
from custom_components.haeo.core.data.loader.source_history import (
    OFF_PERIODS_ATTRIBUTE,
    READINGS_ATTRIBUTE,
    OffPeriod,
    Reading,
    all_off,
    history_attributes,
    is_off_state,
    is_on_state,
    off_periods,
    off_periods_field,
    read_off_periods,
    read_readings,
    readings,
    readings_field,
    takes_history,
    value_at,
)
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.elements.ev import (
    CONF_CONNECTED,
    CONF_CONNECTED_OFF_PERIODS,
    CONF_ODOMETER,
    CONF_ODOMETER_READINGS,
)


@pytest.mark.parametrize(
    ("raw", "off", "on"),
    [
        ("off", True, False),
        ("False", True, False),
        ("0", True, False),
        ("on", False, True),
        ("true", False, True),
        ("1", False, True),
        ("unavailable", False, False),
        ("unknown", False, False),
        ("nan", False, False),
    ],
)
def test_on_and_off_states(raw: str, *, off: bool, on: bool) -> None:
    """Off, false, and zero read as off; on, true, and one as on; anything else as neither."""
    assert is_off_state(raw) is off
    assert is_on_state(raw) is on


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        pytest.param([("off", 100.0), ("on", 200.0)], [(100.0, 200.0)], id="unplugged_then_plugged_in"),
        pytest.param(
            [("off", 100.0), ("on", 200.0), ("off", 300.0), ("on", 400.0)],
            [(100.0, 200.0), (300.0, 400.0)],
            id="two_unplugs",
        ),
        pytest.param([("on", 100.0), ("off", 200.0)], [(200.0, None)], id="still_off"),
        pytest.param(
            [("off", 100.0), ("unavailable", 150.0), ("on", 200.0)], [(100.0, 200.0)], id="unavailable_stays_off"
        ),
        pytest.param(
            [("off", 100.0), ("unknown", 150.0), ("off", 160.0), ("on", 200.0)],
            [(100.0, 200.0)],
            id="restart_while_off_stays_off",
        ),
        pytest.param([("on", 100.0), ("unavailable", 150.0), ("on", 200.0)], [], id="restart_is_not_off"),
        pytest.param([], [], id="no_history"),
    ],
)
def test_off_periods(changes: list[tuple[str, float]], expected: list[OffPeriod]) -> None:
    """An off period runs from the first off reading to the next on reading."""
    assert off_periods(changes) == expected


def test_readings_skip_unparseable_states() -> None:
    """Readings keep numeric states only."""
    assert readings([("100.5", 10.0), ("unavailable", 20.0), ("101", 30.0)]) == [(10.0, 100.5), (30.0, 101.0)]


@pytest.mark.parametrize(
    ("output_type", "changes", "expected"),
    [
        (OutputType.AVAILABILITY, [("off", 100.0)], {OFF_PERIODS_ATTRIBUTE: [(100.0, None)]}),
        (OutputType.DISTANCE, [("10050.5", 100.0)], {READINGS_ATTRIBUTE: [(100.0, 10050.5)]}),
        (OutputType.POWER, [("5", 100.0)], None),
    ],
)
def test_history_follows_output_type(
    output_type: OutputType, changes: list[tuple[str, float]], expected: dict[str, object] | None
) -> None:
    """Availability inputs get off periods, distance inputs get readings, and others get none."""
    assert takes_history(output_type) is (expected is not None)
    assert history_attributes(output_type, changes) == expected


@pytest.mark.parametrize(
    ("attribute", "expected"),
    [
        pytest.param([[100.0, 200.0], [300, None]], [(100.0, 200.0), (300.0, None)], id="captured_json"),
        pytest.param([(100.0, None)], [(100.0, None)], id="tuples"),
        pytest.param([[100.0]], None, id="not_a_pair"),
        pytest.param([["100", None]], None, id="string_start"),
        pytest.param([[100.0, True]], None, id="bool_end"),
        pytest.param("100", None, id="string"),
    ],
)
def test_read_off_periods(attribute: object, expected: list[OffPeriod] | None) -> None:
    """Off periods read back from injected or captured attributes, and malformed ones are ignored."""
    state = FakeEntityState("binary_sensor.plug", "on", {OFF_PERIODS_ATTRIBUTE: attribute})
    assert read_off_periods(state) == expected


@pytest.mark.parametrize(
    ("attribute", "expected"),
    [
        pytest.param([[10.0, 100.5], [20, 101]], [(10.0, 100.5), (20.0, 101.0)], id="captured_json"),
        pytest.param([[10.0, None]], None, id="missing_value"),
    ],
)
def test_read_readings(attribute: object, expected: list[Reading] | None) -> None:
    """Readings read back from injected or captured attributes, and malformed ones are ignored."""
    state = FakeEntityState("sensor.odometer", "101", {READINGS_ATTRIBUTE: attribute})
    assert read_readings(state) == expected


def test_reading_history_without_state_or_attribute() -> None:
    """A missing state or attribute carries no history."""
    assert read_off_periods(None) is None
    assert read_readings(FakeEntityState("sensor.odometer", "101", {})) is None


@pytest.mark.parametrize(
    ("per_source", "expected"),
    [
        pytest.param([[(100.0, 200.0)]], [(100.0, 200.0)], id="one_source"),
        pytest.param([[(100.0, 300.0)], [(200.0, None)]], [(200.0, 300.0)], id="overlap"),
        pytest.param([[(100.0, 200.0)], [(300.0, None)]], [], id="never_all_off"),
        pytest.param([[(100.0, None)], [(150.0, None)]], [(150.0, None)], id="both_still_off"),
        pytest.param([], [], id="no_sources"),
    ],
)
def test_all_off(per_source: list[list[OffPeriod]], expected: list[OffPeriod]) -> None:
    """Several plugged-in sensors read unplugged only while all of them are off."""
    assert all_off(per_source) == expected


@pytest.mark.parametrize(
    ("at", "expected"),
    [(5.0, None), (10.0, 100.0), (15.0, 100.0), (25.0, 102.0)],
)
def test_value_at(at: float, expected: float | None) -> None:
    """The value at a time is the latest reading at or before it."""
    assert value_at([(10.0, 100.0), (20.0, 102.0)], at) == expected


def test_ev_history_keys_match_loader_convention() -> None:
    """The EV schema's history keys are the ones the loader writes beside its fields."""
    assert off_periods_field(CONF_CONNECTED) == CONF_CONNECTED_OFF_PERIODS
    assert readings_field(CONF_ODOMETER) == CONF_ODOMETER_READINGS
