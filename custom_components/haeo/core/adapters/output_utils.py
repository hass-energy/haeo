"""Utilities for validating adapter output mappings."""

from collections.abc import Mapping
from typing import overload

from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER, CONNECTION_SEGMENTS
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
    """Return a connection's power at its measured point, or zeros when the connection is absent.

    Policy compilation drops connections that no tagged source can reach. Adapters
    still run for the configured element, so a pruned connection is treated as
    carrying no flow rather than failing output extraction.
    """
    if connection_outputs is None:
        return OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(0.0,) * period_count, direction="+")
    return expect_output_data(connection_outputs[CONNECTION_POWER])


def power_limit_shadow_price(
    connection_outputs: Mapping[ModelOutputName, ModelOutputValue] | None,
) -> OutputData | None:
    """Return the shadow price of a connection's power limit segment, or None when it has none."""
    segments = connection_outputs.get(CONNECTION_SEGMENTS) if connection_outputs is not None else None
    power_limit = segments.get("power_limit") if isinstance(segments, Mapping) else None
    return expect_output_data(power_limit.get("power_limit")) if isinstance(power_limit, Mapping) else None


__all__ = ["connection_power", "expect_output_data", "power_limit_shadow_price"]
