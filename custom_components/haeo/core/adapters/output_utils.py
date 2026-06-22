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


def connection_power(
    connection_outputs: Mapping[ModelOutputName, ModelOutputValue] | None,
    period_count: int,
) -> OutputData:
    """Return a connection's source-end (pre-segment) power output.

    For a connection with an efficiency segment, this is the flow *before*
    efficiency is applied. Use :func:`connection_power_out` for the post-
    efficiency, target-end flow.

    Policy compilation drops connections that no tagged source can reach. Adapters
    still run for the configured element, so a pruned connection is treated as
    carrying no flow rather than failing output extraction.
    """
    if connection_outputs is None:
        return OutputData(type=OutputType.POWER_FLOW, unit="kW", values=[0.0] * period_count, direction="+")
    return expect_output_data(connection_outputs[CONNECTION_POWER])


def connection_power_out(
    connection_outputs: Mapping[ModelOutputName, ModelOutputValue] | None,
    period_count: int,
) -> OutputData:
    """Return a connection's target-end (post-segment) power output.

    For a connection with an efficiency segment, this is the flow *after*
    efficiency is applied. Use :func:`connection_power` for the pre-
    efficiency, source-end flow.

    Policy compilation drops connections that no tagged source can reach. Adapters
    still run for the configured element, so a pruned connection is treated as
    carrying no flow rather than failing output extraction.
    """
    if connection_outputs is None:
        return OutputData(type=OutputType.POWER_FLOW, unit="kW", values=[0.0] * period_count, direction="+")
    return expect_output_data(connection_outputs[CONNECTION_POWER_OUT])


__all__ = ["connection_power", "connection_power_out", "expect_output_data"]
