"""Tests for OutputData class."""

from custom_components.haeo.model.const import OUTPUT_TYPE_POWER
from custom_components.haeo.model.output_data import OutputData


def test_single_value() -> None:
    """Single value is wrapped in a tuple."""
    output = OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=5.0)
    assert output.values == (5.0,)


def test_sequence() -> None:
    """Sequence values are extracted correctly."""
    output = OutputData(type=OUTPUT_TYPE_POWER, unit="kW", values=[1.0, 2.0, 3.0])
    assert output.values == (1.0, 2.0, 3.0)
