"""Utilities for validating adapter output mappings."""

from typing import overload

from custom_components.haeo.model import ModelOutputValue
from custom_components.haeo.model.output_data import OutputData


@overload
def expect_output_data(value: None) -> None: ...


@overload
def expect_output_data(value: OutputData) -> OutputData: ...


@overload
def expect_output_data(value: ModelOutputValue) -> OutputData: ...


def expect_output_data(value: ModelOutputValue | None) -> OutputData | None:
    """Return OutputData when present, or None."""
    if value is None:
        return None
    if not isinstance(value, OutputData):
        raise TypeError
    return value


__all__ = ["expect_output_data"]
