"""Tests for OutputData class."""

import numpy as np

from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.output_data import OutputData


def test_single_value() -> None:
    """Single value is wrapped in a tuple."""
    output = OutputData(type=OutputType.POWER, unit="kW", values=5.0)
    assert output.values == (5.0,)


def test_sequence() -> None:
    """Sequence values are extracted correctly."""
    output = OutputData(type=OutputType.POWER, unit="kW", values=[1.0, 2.0, 3.0])
    assert output.values == (1.0, 2.0, 3.0)


def test_numpy_array() -> None:
    """Numpy arrays are flattened to tuple."""
    output = OutputData(type=OutputType.POWER, unit="kW", values=np.array([1.0, 2.0, 3.0]))
    assert output.values == (1.0, 2.0, 3.0)
