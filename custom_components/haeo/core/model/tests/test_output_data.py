"""Tests for OutputData class."""

from dataclasses import replace

import pytest

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.output_data import OutputData


@pytest.mark.parametrize(
    "values",
    [
        pytest.param([1.0, 2.0], id="list"),
        pytest.param("ok", id="str"),
        pytest.param(1.0, id="float"),
    ],
)
def test_values_that_are_not_a_tuple_are_rejected(values: object) -> None:
    """Values replaced with anything but a tuple fail at once, rather than being split or stored as given."""
    output = OutputData(type=OutputType.STATUS, unit=None, values=("ok",))

    with pytest.raises(TypeError, match="must be a tuple"):
        replace(output, values=values)
