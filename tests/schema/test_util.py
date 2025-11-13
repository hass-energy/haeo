"""Tests for schema utility functions."""

from enum import Enum

from homeassistant.const import UnitOfPower
import pytest

from custom_components.haeo.schema.fields import SensorFieldMeta
from custom_components.haeo.schema.util import UnitSpec, matches_unit_spec


class TestCurrency(Enum):
    """Mock currency enum for testing."""

    USD = "$"
    AUD = "AUD"
    EUR = "EUR"


# Test cases for matches_unit_spec: (unit, pattern, expected)
UNIT_MATCHING_TEST_CASES = [
    # Exact string matches
    ("kW", "kW", True),
    ("kW", "W", False),
    ("kWh", "kWh", True),
    ("Wh", "kWh", False),
    # Wildcard patterns - prefix
    ("$/kWh", ("*", "/", "kWh"), True),
    ("AUD/kWh", ("*", "/", "kWh"), True),
    ("EUR/kWh", ("*", "/", "kWh"), True),
    ("USD/kWh", ("*", "/", "kWh"), True),
    ("GBP/kWh", ("*", "/", "kWh"), True),
    ("¢/kWh", ("*", "/", "kWh"), True),
    ("kWh", ("*", "/", "kWh"), False),
    ("$/MWh", ("*", "/", "kWh"), False),
    ("kW", ("*", "/", "kWh"), False),
    # Wildcard patterns - suffix
    ("$/kWh", ("kWh", "/", "*"), False),
    ("kWh/day", ("kWh", "/", "*"), True),
    ("kWh/$", ("kWh", "/", "*"), True),
    ("Wh/day", ("kWh", "/", "*"), False),
    ("$/kWh", ("$", "/", "*"), True),
    ("$/MWh", ("$", "/", "*"), True),
    ("AUD/kWh", ("$", "/", "*"), False),
    # Wildcard patterns - middle and multiple
    ("prefix_MIDDLE_suffix", ("prefix", "*", "suffix"), True),
    ("prefix_MIDDLE_suffix_END", ("prefix", "*", "suffix", "*"), True),
    ("ABC_DEF_GHI", ("*", "_", "*", "_", "*"), True),
    # Empty strings
    ("", "", True),
    ("kWh", "", False),
    ("", "kWh", False),
    # Empty tuple
    ("", (), True),
    ("kWh", (), False),
    # Case sensitivity
    ("kWh", "kWh", True),
    ("KWH", "kWh", False),
    ("kwh", "kWh", False),
    # Enum membership
    ("kW", UnitOfPower, True),
    ("MW", UnitOfPower, True),
    ("W", UnitOfPower, True),
    ("definitely_not_a_unit_xyz", UnitOfPower, False),
    ("kWh", UnitOfPower, False),
    ("$/kWh", UnitOfPower, False),
    # Tuple patterns - all strings
    ("$/kWh", ("$", "/", "kWh"), True),
    ("AUD/kWh", ("$", "/", "kWh"), False),
    ("$/Wh", ("$", "/", "kWh"), False),
    ("$/MWh", ("$", "/", "kWh"), False),
    # Tuple patterns - with wildcards
    ("$/kWh", ("*", "/", "kWh"), True),
    ("AUD/kWh", ("*", "/", "kWh"), True),
    ("EUR/kWh", ("*", "/", "kWh"), True),
    ("$/Wh", ("*", "/", "kWh"), False),
    ("$/MWh", ("*", "/", "kWh"), False),
    ("kW", ("*", "/", "kWh"), False),
    # Tuple patterns - wrong part count
    ("kWh", ("*", "/", "kWh"), False),
    ("$/AUD/kWh", ("*", "/", "kWh"), False),
    # Tuple patterns - enum as iterable (concatenated without separator)
    ("WWh", UnitOfPower, False),  # UnitOfPower contains "W", not "WWh"
    ("kW", UnitOfPower, True),  # Exact match for enum value
    ("W", UnitOfPower, True),  # Exact match for enum value
    # Sequences of specs
    ("kW", ["kW", "MW"], True),
    ("kW", ["W", "MW"], False),
    ("kW", [UnitOfPower, "GW"], True),
]


@pytest.mark.parametrize(("unit", "pattern", "expected"), UNIT_MATCHING_TEST_CASES)
def test_matches_unit_spec(unit: str, pattern: UnitSpec | list[UnitSpec], *, expected: bool) -> None:
    """Test unit matching logic with comprehensive pattern coverage.

    This tests matches_unit_spec() which is the core unit matching function.
    Other components like EntityMetadata.is_compatible_with() delegate to this,
    so testing this function provides full coverage.
    """
    assert matches_unit_spec(unit, pattern) == expected


# Test cases for SensorFieldMeta: (accepted_units, multiple, expected_field_type_platform)
SENSOR_FIELD_META_TEST_CASES = [
    # Enum type - uses first enum value (don't test specific value)
    (UnitOfPower, False, "sensor"),
    # Sequence of strings
    (["kW", "MW"], False, "sensor"),
    # Tuple pattern - concatenates to string
    (("*", "/", "kWh"), False, "sensor"),
    # Mixed sequence
    (["kW", ("*", "/", "kWh")], True, "sensor"),
]


@pytest.mark.parametrize(
    ("accepted_units", "multiple", "expected_platform"),
    SENSOR_FIELD_META_TEST_CASES,
)
def test_sensor_field_meta(
    accepted_units: UnitSpec | list[UnitSpec],
    expected_platform: str,
    *,
    multiple: bool,
) -> None:
    """Test SensorFieldMeta initialization and properties."""
    meta = SensorFieldMeta(accepted_units=accepted_units, multiple=multiple)
    assert meta.accepted_units == accepted_units
    assert meta.multiple == multiple
    assert meta.field_type == expected_platform
