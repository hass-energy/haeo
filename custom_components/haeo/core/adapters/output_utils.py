"""Utilities for validating adapter output mappings."""

from collections.abc import Mapping, Sequence
import re
from typing import Any, overload

import numpy as np

from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER
from custom_components.haeo.core.model.output_data import OutputData

_RANGE_UP_EPS = 1e-9

_TAG_POWER_BALANCE_PATTERN = re.compile(
    r"^(?P<prefix>battery_section|inverter_dc_bus|battery|node)_tag_(?P<tag>\d+)_power_balance$"
)


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
    """Return a connection's power output, or zeros when the connection is absent.

    Policy compilation drops connections that no tagged source can reach. Adapters
    still run for the configured element, so a pruned connection is treated as
    carrying no flow rather than failing output extraction.
    """
    if connection_outputs is None:
        return OutputData(type=OutputType.POWER_FLOW, unit="kW", values=[0.0] * period_count, direction="+")
    return expect_output_data(connection_outputs[CONNECTION_POWER])


def split_balance_shadow_rows(
    dual: OutputData,
    n_periods: int,
) -> tuple[np.ndarray, np.ndarray | None] | None:
    """Reshape flat balance-constraint rows into (n_tags, n_periods)."""
    duals = np.asarray(dual.values, dtype=float)
    if len(duals) == n_periods:
        return duals.reshape(1, n_periods), _reshape_ranging(dual.range_up, n_periods, n_tags=1)
    if len(duals) % n_periods != 0:
        return None
    n_tags = len(duals) // n_periods
    return duals.reshape(n_tags, n_periods), _reshape_ranging(dual.range_up, n_periods, n_tags)


def marginal_balance_dual_per_step(
    duals_by_tag: np.ndarray,
    range_up_by_tag: np.ndarray | None,
) -> np.ndarray:
    """Select the cheapest available balance dual at each timestep."""
    n_tags, n_periods = duals_by_tag.shape
    if n_tags == 1:
        return duals_by_tag[0]

    marginal = np.empty(n_periods, dtype=float)
    for t in range(n_periods):
        if range_up_by_tag is not None:
            available = range_up_by_tag[:, t] > _RANGE_UP_EPS
            if np.any(available):
                marginal[t] = float(np.min(duals_by_tag[available, t]))
                continue
            marginal[t] = float(np.max(duals_by_tag[:, t]))
            continue
        marginal[t] = float(np.min(duals_by_tag[:, t]))
    return marginal


def collapse_balance_shadow_price(dual: OutputData, n_periods: int) -> OutputData:
    """Collapse per-tag balance dual blocks to one ``n_periods`` series for HA sensors."""
    split = split_balance_shadow_rows(dual, n_periods)
    if split is None:
        return dual
    duals_by_tag, range_up_by_tag = split
    marginal = marginal_balance_dual_per_step(duals_by_tag, range_up_by_tag)
    return OutputData(
        type=dual.type,
        unit=dual.unit,
        values=tuple(float(value) for value in marginal),
        direction=dual.direction,
        advanced=dual.advanced,
        state_last=dual.state_last,
        state=dual.state,
        priority=dual.priority,
        fixed=dual.fixed,
        display_precision=dual.display_precision,
    )


def per_tag_balance_shadow_price_outputs(
    *,
    element_prefix: str,
    dual: OutputData,
    n_periods: int,
) -> dict[str, OutputData]:
    """Return per-tag balance shadow price outputs keyed by ``{prefix}_tag_{tag}_power_balance``."""
    split = split_balance_shadow_rows(dual, n_periods)
    if split is None:
        return {}
    duals_by_tag, range_up_by_tag = split
    if duals_by_tag.shape[0] <= 1:
        return {}

    tag_ids = tuple(dual.balance_tags) if dual.balance_tags is not None else tuple(range(1, duals_by_tag.shape[0] + 1))
    if len(tag_ids) != duals_by_tag.shape[0]:
        return {}

    outputs: dict[str, OutputData] = {}
    for tag_index, tag in enumerate(tag_ids):
        tag_values = duals_by_tag[tag_index]
        tag_range_up = None if range_up_by_tag is None else tuple(float(v) for v in range_up_by_tag[tag_index])
        tag_range_dn = None if dual.range_dn is None else _tag_block(dual.range_dn, n_periods, tag_index)
        outputs[f"{element_prefix}_tag_{tag}_power_balance"] = OutputData(
            type=dual.type,
            unit=dual.unit,
            values=tuple(float(value) for value in tag_values),
            direction=dual.direction,
            advanced=True,
            state_last=dual.state_last,
            display_precision=dual.display_precision,
            range_up=tag_range_up,
            range_dn=tag_range_dn,
        )
    return outputs


def balance_shadow_price_device_outputs(
    *,
    element_prefix: str,
    primary_output_name: str,
    dual: OutputData,
    n_periods: int,
) -> dict[str, OutputData]:
    """Build collapsed and per-tag balance shadow price outputs for HA surfacing."""
    outputs: dict[str, OutputData] = {
        primary_output_name: collapse_balance_shadow_price(dual, n_periods),
    }
    outputs.update(
        per_tag_balance_shadow_price_outputs(
            element_prefix=element_prefix,
            dual=dual,
            n_periods=n_periods,
        )
    )
    return outputs


def tag_power_balance_translation(output_name: str) -> tuple[str, dict[str, str]] | None:
    """Resolve dynamic per-tag output names to translation keys and placeholders."""
    match = _TAG_POWER_BALANCE_PATTERN.match(output_name)
    if match is None:
        return None
    prefix = match.group("prefix")
    tag = match.group("tag")
    return f"{prefix}_tag_power_balance", {"tag": tag}


def _reshape_ranging(
    range_up: Sequence[Any] | None,
    n_periods: int,
    n_tags: int,
) -> np.ndarray | None:
    """Reshape flat ranging rows to match per-tag dual blocks."""
    if range_up is None:
        return None
    ranging = np.asarray(range_up, dtype=float)
    expected = n_tags * n_periods
    if len(ranging) != expected:
        return None
    return ranging.reshape(n_tags, n_periods)


def _tag_block(flat: Sequence[Any], n_periods: int, tag_index: int) -> tuple[float, ...] | None:
    """Extract one tag block from a flat per-tag sequence."""
    values = np.asarray(flat, dtype=float)
    if len(values) % n_periods != 0:
        return None
    n_tags = len(values) // n_periods
    if tag_index >= n_tags:
        return None
    return tuple(float(value) for value in values.reshape(n_tags, n_periods)[tag_index])


__all__ = [
    "balance_shadow_price_device_outputs",
    "collapse_balance_shadow_price",
    "connection_power",
    "expect_output_data",
    "marginal_balance_dual_per_step",
    "per_tag_balance_shadow_price_outputs",
    "split_balance_shadow_rows",
    "tag_power_balance_translation",
]
