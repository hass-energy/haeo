"""Tests for calendar event parsing and trip window extraction."""

from datetime import UTC, datetime

import pytest

from custom_components.haeo.core.data.loader.calendar import (
    TripEventData,
    TripWindow,
    extract_trip_windows,
    parse_distance,
)

# --- parse_distance tests ---


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        pytest.param("50 km", (50.0, "km"), id="km_with_space"),
        pytest.param("50km", (50.0, "km"), id="km_no_space"),
        pytest.param("30 mi", (30.0, "mi"), id="mi_with_space"),
        pytest.param("30mi", (30.0, "mi"), id="mi_no_space"),
        pytest.param("100.5 miles", (100.5, "mi"), id="miles_decimal"),
        pytest.param("15.2 m", (15.2, "m"), id="meters"),
        pytest.param("200 meters", (200.0, "m"), id="meters_long"),
        pytest.param("10 kilometer", (10.0, "km"), id="kilometer_singular"),
        pytest.param("10 kilometres", (10.0, "km"), id="kilometres_british"),
        pytest.param("5 ft", (5.0, "ft"), id="feet"),
        pytest.param("3 yd", (3.0, "yd"), id="yards"),
        pytest.param("3 yards", (3.0, "yd"), id="yards_long"),
        pytest.param("  50 km  ", (50.0, "km"), id="whitespace_padded"),
    ],
)
def test_parse_distance_valid(location: str, expected: tuple[float, str]) -> None:
    """Valid distance strings parse correctly."""
    assert parse_distance(location) == expected


@pytest.mark.parametrize(
    "location",
    [
        pytest.param("", id="empty"),
        pytest.param("no number here", id="no_number"),
        pytest.param("50", id="no_unit"),
        pytest.param("50 fathoms", id="unknown_unit"),
        pytest.param("km 50", id="unit_before_number"),
        pytest.param("50 km extra", id="extra_text"),
    ],
)
def test_parse_distance_invalid(location: str) -> None:
    """Invalid distance strings return None."""
    assert parse_distance(location) is None


# --- extract_trip_windows tests ---


def _dt(hour: int, minute: int = 0) -> datetime:
    """Create a UTC datetime on a fixed date for testing."""
    return datetime(2024, 1, 15, hour, minute, tzinfo=UTC)


def test_extract_trip_windows_basic() -> None:
    """Trip window extracted with correct energy calculation."""
    events = [
        TripEventData(start=_dt(8), end=_dt(10), location="50 km"),
    ]
    result = extract_trip_windows(events, energy_per_distance=0.2, distance_unit="km", ha_default_distance_unit="km")
    assert len(result) == 1
    assert result[0] == TripWindow(start=_dt(8), end=_dt(10), distance=50.0, energy_kwh=10.0)


def test_extract_trip_windows_no_location() -> None:
    """Missing location results in zero-distance trip."""
    events = [
        TripEventData(start=_dt(8), end=_dt(10), location=None),
    ]
    result = extract_trip_windows(events, energy_per_distance=0.2, distance_unit="km", ha_default_distance_unit="km")
    assert len(result) == 1
    assert result[0].distance == 0.0
    assert result[0].energy_kwh == 0.0


def test_extract_trip_windows_unparseable_location() -> None:
    """Invalid location string results in zero-distance trip."""
    events = [
        TripEventData(start=_dt(8), end=_dt(10), location="office"),
    ]
    result = extract_trip_windows(events, energy_per_distance=0.2, distance_unit="km", ha_default_distance_unit="km")
    assert len(result) == 1
    assert result[0].distance == 0.0
    assert result[0].energy_kwh == 0.0


def test_extract_trip_windows_end_before_start_skipped() -> None:
    """Events where end <= start are filtered out."""
    events = [
        TripEventData(start=_dt(10), end=_dt(8), location="50 km"),
        TripEventData(start=_dt(10), end=_dt(10), location="50 km"),
    ]
    result = extract_trip_windows(events, energy_per_distance=0.2, distance_unit="km", ha_default_distance_unit="km")
    assert result == []


def test_extract_trip_windows_sorted_by_start() -> None:
    """Results are sorted by start time regardless of input order."""
    events = [
        TripEventData(start=_dt(14), end=_dt(16), location="30 km"),
        TripEventData(start=_dt(8), end=_dt(10), location="50 km"),
    ]
    result = extract_trip_windows(events, energy_per_distance=0.2, distance_unit="km", ha_default_distance_unit="km")
    assert len(result) == 2
    assert result[0].start == _dt(8)
    assert result[1].start == _dt(14)


def test_extract_trip_windows_unit_conversion() -> None:
    """Distance is converted to the energy_per_distance unit when different."""
    events = [
        TripEventData(start=_dt(8), end=_dt(10), location="30 mi"),
    ]

    def mock_convert(value: float, from_unit: str, to_unit: str) -> float:
        assert from_unit == "mi"
        assert to_unit == "km"
        return value * 1.60934

    result = extract_trip_windows(
        events,
        energy_per_distance=0.2,
        distance_unit="km",
        ha_default_distance_unit="km",
        convert_distance=mock_convert,
    )
    assert len(result) == 1
    assert result[0].distance == pytest.approx(48.2802, rel=1e-3)
    assert result[0].energy_kwh == pytest.approx(9.6560, rel=1e-3)


def test_extract_trip_windows_same_unit_no_conversion() -> None:
    """No unit conversion occurs when event unit matches energy_per_distance unit."""
    events = [
        TripEventData(start=_dt(8), end=_dt(10), location="50 km"),
    ]

    def should_not_be_called(value: float, from_unit: str, to_unit: str) -> float:
        msg = "Conversion should not be called"
        raise AssertionError(msg)

    result = extract_trip_windows(
        events,
        energy_per_distance=0.2,
        distance_unit="km",
        ha_default_distance_unit="km",
        convert_distance=should_not_be_called,
    )
    assert len(result) == 1
    assert result[0].distance == 50.0
