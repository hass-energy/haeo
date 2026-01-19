"""Utilities for validating adapter output mappings."""

from collections.abc import Mapping

from custom_components.haeo.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.model.output_data import OutputData


def expect_output_data_map(
    name: str,
    outputs: Mapping[ModelOutputName, ModelOutputValue],
) -> dict[ModelOutputName, OutputData]:
    """Return outputs as OutputData values or raise a TypeError."""
    result: dict[ModelOutputName, OutputData] = {}
    for key, value in outputs.items():
        if not isinstance(value, OutputData):
            msg = f"Expected OutputData for {name!r} output {key!r}"
            raise TypeError(msg)
        result[key] = value
    return result


__all__ = ["expect_output_data_map"]
