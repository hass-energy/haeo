"""Tests for schema utility functions."""

from enum import Enum

from homeassistant.const import UnitOfPower
import pytest

from custom_components.haeo.schema.fields import EntitySelect, TimeSeries
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
    ("a/b/c", ("a", "/", "b"), False),
    ("a/b", ("a", "/", "b", "/", "c"), False),
    # Special case from pricing - $ with wildcard
    ("$/kWh", ("$", "/", "*"), True),
    ("$/MWh", ("$", "/", "*"), True),
    ("$/Wh", ("$", "/", "*"), True),
    ("AUD/kWh", ("$", "/", "*"), False),
]


@pytest.mark.parametrize(("unit", "pattern", "expected"), UNIT_MATCHING_TEST_CASES)
def test_matches_unit_spec(unit: str, pattern: UnitSpec, *, expected: bool) -> None:
    """Unit patterns should match units according to specification."""
    result = matches_unit_spec(unit, pattern)
    assert result == expected, f"Expected {unit!r} to {'match' if expected else 'not match'} {pattern!r}"


def test_entity_select_stores_accepted_units() -> None:
    """EntitySelect should store accepted_units for filtering."""
    validator = EntitySelect(accepted_units=UnitOfPower, multiple=True)

    assert validator.accepted_units == UnitOfPower
    assert validator.multiple is True


def test_time_series_stores_accepted_units() -> None:
    """TimeSeries should store accepted_units for filtering."""
    loader = TimeSeries(accepted_units=UnitOfPower, multiple=False)

    assert loader.accepted_units == UnitOfPower
    assert loader.multiple is False


PRICE_UNITS: list[UnitSpec] = [("*", "/", "kWh"), ("*", "/", "MWh"), ("*", "/", "Wh")]


@pytest.mark.parametrize(
    "price_pattern",
    PRICE_UNITS,
)
def test_price_patterns_match_common_currencies(price_pattern: tuple[str, ...]) -> None:
    """Price unit patterns should match common currency symbols."""
    currencies = ["$", "USD", "AUD", "EUR", "¢", "€", "£", "GBP"]
    energy_suffix = price_pattern[-1]

    for currency in currencies:
        unit = f"{currency}/{energy_suffix}"
        assert matches_unit_spec(unit, price_pattern), f"{unit} should match {price_pattern}"
