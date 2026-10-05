"""Utilities for validating adapter output mappings."""

from collections.abc import Mapping
from typing import overload

from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER, CONNECTION_POWER_OUT
from custom_components.haeo.core.model.output_data import OutputData


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


def _connection_output(
    connection_outputs: Mapping[ModelOutputName, ModelOutputValue] | None,
    output_name: ModelOutputName,
    period_count: int,
) -> OutputData:
    """Return one of a connection's power outputs, or zeros when the connection is absent.

    Policy compilation drops connections that no tagged source can reach. Adapters
    still run for the configured element, so a pruned connection is treated as
    carrying no flow rather than failing output extraction.
    """
    if connection_outputs is None:
        return OutputData(type=OutputType.POWER_FLOW, unit="kW", values=[0.0] * period_count, direction="+")
    return expect_output_data(connection_outputs[output_name])


def connection_power(
    connection_outputs: Mapping[ModelOutputName, ModelOutputValue] | None,
    period_count: int,
) -> OutputData:
    """Return the power entering a connection at its source end, before efficiency losses."""
    return _connection_output(connection_outputs, CONNECTION_POWER, period_count)


def connection_power_out(
    connection_outputs: Mapping[ModelOutputName, ModelOutputValue] | None,
    period_count: int,
) -> OutputData:
    """Return the power leaving a connection at its target end, after efficiency losses."""
    return _connection_output(connection_outputs, CONNECTION_POWER_OUT, period_count)


__all__ = ["connection_power", "connection_power_out", "expect_output_data"]
