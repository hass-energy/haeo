"""Tests for adapter output utilities."""

import numpy as np

from custom_components.haeo.core.adapters.output_utils import (
    balance_shadow_price_device_outputs,
    collapse_balance_shadow_price,
    marginal_balance_dual_per_step,
    split_balance_shadow_rows,
    tag_power_balance_translation,
)
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.output_data import OutputData


def test_split_balance_shadow_rows_single_tag() -> None:
    """Single-tag duals reshape to one row."""
    dual = OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.1, 0.2))
    split = split_balance_shadow_rows(dual, n_periods=2)
    assert split is not None
    duals_by_tag, range_up = split
    assert duals_by_tag.shape == (1, 2)
    assert range_up is None


def test_marginal_balance_dual_prefers_available_tag() -> None:
    """Marginal dual uses the cheapest tag with ranging headroom."""
    duals = np.array([[0.5, 0.5], [0.2, 0.8]])
    range_up = np.array([[0.0, 0.0], [1.0, 0.0]])
    marginal = marginal_balance_dual_per_step(duals, range_up)
    assert marginal.tolist() == [0.2, 0.8]


def test_collapse_balance_shadow_price_preserves_single_tag() -> None:
    """Single-tag networks pass through unchanged."""
    dual = OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.3, 0.4))
    collapsed = collapse_balance_shadow_price(dual, n_periods=2)
    assert collapsed.values == (0.3, 0.4)


def test_balance_shadow_price_device_outputs_adds_per_tag_sensors() -> None:
    """Multi-tag duals produce collapsed primary output and per-tag diagnostics."""
    dual = OutputData(
        type=OutputType.SHADOW_PRICE,
        unit="$/kWh",
        values=(0.1, 0.2, 0.3, 0.4),
        range_up=(1.0, 1.0, 0.0, 0.0),
        balance_tags=(1, 2),
    )
    outputs = balance_shadow_price_device_outputs(
        element_prefix="node",
        primary_output_name="node_power_balance",
        dual=dual,
        n_periods=2,
    )
    assert outputs["node_power_balance"].values == (0.1, 0.2)
    assert outputs["node_tag_1_power_balance"].values == (0.1, 0.2)
    assert outputs["node_tag_2_power_balance"].values == (0.3, 0.4)
    assert outputs["node_tag_1_power_balance"].advanced is True


def test_tag_power_balance_translation() -> None:
    """Dynamic per-tag output names map to translation templates."""
    resolved = tag_power_balance_translation("node_tag_2_power_balance")
    assert resolved == ("node_tag_power_balance", {"tag": "2"})


def test_split_balance_shadow_rows_rejects_invalid_length() -> None:
    """Invalid flat lengths return None."""
    dual = OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.1, 0.2, 0.3))
    assert split_balance_shadow_rows(dual, n_periods=2) is None
