"""Utilities for validating adapter output mappings."""

from collections.abc import Mapping

from custom_components.haeo.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.model.output_data import OutputData


def expect_output_data(value: ModelOutputValue) -> OutputData:
    """Return value as OutputData or raise a TypeError."""
    if not isinstance(value, OutputData):
        raise TypeError
    return value


def maybe_output_data(value: ModelOutputValue | None) -> OutputData | None:
    """Return OutputData for value if present, else None."""
    if value is None:
        return None
    return expect_output_data(value)


def expect_output_data_map(
    outputs: Mapping[ModelOutputName, ModelOutputValue],
) -> dict[ModelOutputName, OutputData]:
    """Return outputs as OutputData values or raise a TypeError."""
    result: dict[ModelOutputName, OutputData] = {}
    for key, value in outputs.items():
        result[key] = expect_output_data(value)
    return result


__all__ = ["expect_output_data", "expect_output_data_map", "maybe_output_data"]
