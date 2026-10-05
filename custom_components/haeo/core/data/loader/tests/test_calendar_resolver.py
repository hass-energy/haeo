"""Tests for resolving calendar schema values into boundary arrays."""

import numpy as np
import pytest

from conftest import FakeEntityState, FakeStateMachine
from custom_components.haeo.core.data.loader.calendar_resolver import is_calendar_boundary_data, resolve_calendar_field
from custom_components.haeo.core.schema.calendar_value import CalendarValue, as_calendar_value
from custom_components.haeo.core.schema.field_hints import CalendarFieldHint

# Hourly boundaries: 4 boundaries defining 3 periods, starting at epoch 0 (UTC).
BOUNDARY_TIMES: tuple[float, ...] = (0.0, 3600.0, 7200.0, 10800.0)

ENTITY_ID = "calendar.trips"


def _calendar_value(events: list[dict[str, str | None]] | None) -> CalendarValue:
    """Build a calendar schema value with optional captured events."""
    value = as_calendar_value(ENTITY_ID)
    if events is not None:
        value["events"] = events  # type: ignore[typeddict-item]  # test fixtures use plain dicts
    return value


def _event(start_ts: float, end_ts: float, location: str | None = None) -> dict[str, str | None]:
    """Build a captured event dict spanning the given epoch seconds."""
    from datetime import UTC, datetime  # noqa: PLC0415

    return {
        "start": datetime.fromtimestamp(start_ts, tz=UTC).isoformat(),
        "end": datetime.fromtimestamp(end_ts, tz=UTC).isoformat(),
        "summary": "Trip",
        "location": location,
        "description": None,
    }


def test_distance_event_produces_boundary_arrays() -> None:
    """A distance event fills presence and value arrays at covered boundaries."""
    value = _calendar_value([_event(3600.0, 7200.0, location="50 km")])
    result = resolve_calendar_field(value, CalendarFieldHint(parser="distance"), FakeStateMachine({}), BOUNDARY_TIMES)

    assert result is not None
    assert is_calendar_boundary_data(result)
    np.testing.assert_allclose(result["presence"], [0.0, 1.0, 0.0, 0.0])
    np.testing.assert_allclose(result["value_span"], [0.0, 50.0, 0.0, 0.0])
    np.testing.assert_allclose(result["value_edge_start"], [0.0, 50.0, 0.0, 0.0])
    np.testing.assert_allclose(result["value_edge_end"], [0.0, 0.0, 50.0, 0.0])


def test_distance_units_normalize_to_km() -> None:
    """Distances parsed in other units are converted to kilometres."""
    value = _calendar_value([_event(0.0, 3600.0, location="10 mi")])
    result = resolve_calendar_field(value, CalendarFieldHint(parser="distance"), FakeStateMachine({}), BOUNDARY_TIMES)

    assert result is not None
    np.testing.assert_allclose(result["value_edge_start"][0], 16.09344)


def test_presence_parser_ignores_event_text() -> None:
    """Presence parser marks windows with value 1.0 regardless of text."""
    value = _calendar_value([_event(0.0, 7200.0, location=None)])
    result = resolve_calendar_field(value, CalendarFieldHint(parser="presence"), FakeStateMachine({}), BOUNDARY_TIMES)

    assert result is not None
    np.testing.assert_allclose(result["presence"], [1.0, 1.0, 0.0, 0.0])
    np.testing.assert_allclose(result["value_span"], [1.0, 1.0, 0.0, 0.0])


def test_number_parser_reads_plain_numbers() -> None:
    """Number parser extracts a bare numeric value from event text."""
    value = _calendar_value([_event(0.0, 3600.0, location="7.5")])
    result = resolve_calendar_field(value, CalendarFieldHint(parser="number"), FakeStateMachine({}), BOUNDARY_TIMES)

    assert result is not None
    np.testing.assert_allclose(result["value_span"][0], 7.5)


def test_unparseable_event_keeps_window_with_zero_value() -> None:
    """An event whose text holds no parseable value still occupies its window."""
    value = _calendar_value([_event(3600.0, 7200.0, location="Office")])
    result = resolve_calendar_field(value, CalendarFieldHint(parser="distance"), FakeStateMachine({}), BOUNDARY_TIMES)

    assert result is not None
    np.testing.assert_allclose(result["presence"], [0.0, 1.0, 0.0, 0.0])
    np.testing.assert_allclose(result["value_span"], np.zeros(4))
    np.testing.assert_allclose(result["value_edge_start"], np.zeros(4))
    np.testing.assert_allclose(result["value_edge_end"], np.zeros(4))


def test_overlapping_events_clip_presence_and_sum_values() -> None:
    """Overlapping events sum their values but presence stays binary."""
    value = _calendar_value(
        [
            _event(0.0, 3600.0, location="10 km"),
            _event(0.0, 3600.0, location="20 km"),
        ]
    )
    result = resolve_calendar_field(value, CalendarFieldHint(parser="distance"), FakeStateMachine({}), BOUNDARY_TIMES)

    assert result is not None
    np.testing.assert_allclose(result["presence"][0], 1.0)
    np.testing.assert_allclose(result["value_span"][0], 30.0)
    np.testing.assert_allclose(result["value_edge_start"][0], 30.0)


def test_missing_entity_without_captured_events_returns_none() -> None:
    """No entity state and no captured events means the field is not loaded."""
    value = _calendar_value(None)
    result = resolve_calendar_field(value, CalendarFieldHint(), FakeStateMachine({}), BOUNDARY_TIMES)

    assert result is None


def test_available_entity_without_events_resolves_to_zeros() -> None:
    """An available calendar entity with no events produces all-zero arrays."""
    sm = FakeStateMachine({ENTITY_ID: FakeEntityState(ENTITY_ID, "off", {})})
    result = resolve_calendar_field(_calendar_value(None), CalendarFieldHint(), sm, BOUNDARY_TIMES)

    assert result is not None
    np.testing.assert_allclose(result["presence"], np.zeros(4))
    np.testing.assert_allclose(result["value_span"], np.zeros(4))


def test_entity_events_attribute_is_used_when_present() -> None:
    """Events injected into the entity's haeo_events attribute are resolved."""
    sm = FakeStateMachine(
        {ENTITY_ID: FakeEntityState(ENTITY_ID, "on", {"haeo_events": [_event(0.0, 3600.0, location="5 km")]})}
    )
    result = resolve_calendar_field(
        _calendar_value(None),
        CalendarFieldHint(parser="distance"),
        sm,
        BOUNDARY_TIMES,
    )

    assert result is not None
    np.testing.assert_allclose(result["value_span"][0], 5.0)


def test_is_calendar_boundary_data_rejects_other_values() -> None:
    """The boundary-data check rejects unrelated dicts and scalars."""
    assert not is_calendar_boundary_data({"presence": []})
    assert not is_calendar_boundary_data(1.0)
    assert not is_calendar_boundary_data(None)


@pytest.mark.parametrize(
    ("events", "expected"),
    [
        pytest.param([(-3600.0, 3600.0, "10 km")], -3600.0, id="open_before_horizon"),
        pytest.param([(0.0, 3600.0, "10 km")], 0.0, id="opens_at_horizon_start"),
        pytest.param(
            [(-7200.0, -1800.0, "10 km"), (-3600.0, 3600.0, "10 km")],
            -7200.0,
            id="overlapping_events_chain",
        ),
        pytest.param([(-3600.0, 0.0, "10 km"), (0.0, 3600.0, "10 km")], 0.0, id="touching_events_stay_separate"),
        pytest.param([(-3600.0, 0.0, "10 km")], None, id="ended_at_horizon_start"),
        pytest.param([(3600.0, 7200.0, "10 km")], None, id="starts_later"),
        pytest.param([(-3600.0, 3600.0, "Office")], None, id="zero_value_event"),
        pytest.param([], None, id="no_events"),
    ],
)
def test_open_since_reports_start_of_window_open_at_horizon_start(
    events: list[tuple[float, float, str]], expected: float | None
) -> None:
    """open_since is the true start of the window open at the horizon start."""
    value = _calendar_value([_event(start, end, location=location) for start, end, location in events])
    result = resolve_calendar_field(value, CalendarFieldHint(parser="distance"), FakeStateMachine({}), BOUNDARY_TIMES)

    assert result is not None
    assert result["open_since"] == expected
