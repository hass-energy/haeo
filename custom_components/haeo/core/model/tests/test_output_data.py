"""Tests for OutputData class."""

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.output_data import OutputData


def test_values_are_stored_as_a_tuple() -> None:
    """A list of values is copied into a tuple, so later changes to the list do not reach the output."""
    values = [1.0, 2.0, 3.0]
    output = OutputData(type=OutputType.POWER, unit="kW", values=values)
    values.append(4.0)

    assert output.values == (1.0, 2.0, 3.0)
