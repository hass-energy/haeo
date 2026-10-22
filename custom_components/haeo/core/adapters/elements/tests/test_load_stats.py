"""Unit tests for Load adapter full-horizon + next-24h statistics sensors.

The 8 statistics sensors (4 horizon, 4 next-24h) emitted by
``LoadAdapter.outputs`` are exercised end-to-end through the adapter so that
any future change to the output contract is caught by the same suite.
Internal helpers (``_stats_outputs``, ``_next_24h_window_fractions``,
``_safe_divide``, ``_cumsum``) are covered indirectly via these adapter-level
cases.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.load import (
    LOAD_DEVICE_LOAD,
    LOAD_HORIZON_AVERAGE_MARGINAL_PRICE,
    LOAD_HORIZON_ENERGY,
    LOAD_HORIZON_MARGINAL_COST,
    LOAD_HORIZON_RUNTIME,
    LOAD_NEXT_24H_AVERAGE_MARGINAL_PRICE,
    LOAD_NEXT_24H_ENERGY,
    LOAD_NEXT_24H_MARGINAL_COST,
    LOAD_NEXT_24H_RUNTIME,
    LoadAdapter,
    LoadOutputName,
)
from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.load import LoadConfigData


def _config(*, sheddable: bool = True, source: str = "main_bus", n: int = 4) -> LoadConfigData:
    return {
        "element_type": ElementType.LOAD,
        "name": "load",
        "connection": as_connection_target(source),
        "forecast": {"forecast": np.array([1.0] * n)},
        "curtailment": {"curtailment": sheddable},
    }


def _outputs_with_dual(
    *,
    power: tuple[float, ...],
    dual: tuple[float, ...],
    periods: tuple[float, ...],
    source: str = "main_bus",
) -> Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]:
    """Build a model_outputs mapping with a connection power output and a source node dual."""
    return {
        "load:connection": {
            CONNECTION_POWER: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=power, direction="+"),
        },
        source: {
            ELEMENT_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=dual),
        },
    }


def test_horizon_sensors_are_cumulative_with_state_last_set() -> None:
    """Horizon energy/cost/runtime/avg-cost emit cumulative time series with state_last=True."""
    adapter = LoadAdapter()
    power = (1.0, 2.0, 0.0, 4.0)
    dual = (0.10, 0.20, 0.30, 0.40)
    periods = (1.0, 1.0, 1.0, 1.0)

    result = adapter.outputs(
        "load",
        _outputs_with_dual(power=power, dual=dual, periods=periods),
        config=_config(),
        periods=tuple(periods),
    )
    load_outputs = result[LOAD_DEVICE_LOAD]

    energy = load_outputs[LOAD_HORIZON_ENERGY]
    assert energy.unit == "kWh"
    assert energy.type == OutputType.ENERGY
    # Per-interval energy series; state is the horizon total.
    assert tuple(energy.values) == pytest.approx((1.0, 2.0, 0.0, 4.0))
    assert energy.state == pytest.approx(7.0)

    cost = load_outputs[LOAD_HORIZON_MARGINAL_COST]
    assert cost.unit == "$"
    assert cost.type == OutputType.COST
    assert cost.direction == "-"
    # cost[t] = energy[t] * dual[t]: 0.10, 0.40, 0.0, 1.60; total 2.10.
    assert tuple(cost.values) == pytest.approx((0.10, 0.40, 0.0, 1.60))
    assert cost.state == pytest.approx(2.10)

    runtime = load_outputs[LOAD_HORIZON_RUNTIME]
    assert runtime.unit == "h"
    assert runtime.type == OutputType.DURATION
    # Step 2 is shed (p=0); contributes 0h. Per-interval: 1, 1, 0, 1.
    assert tuple(runtime.values) == pytest.approx((1.0, 1.0, 0.0, 1.0))
    assert runtime.state == pytest.approx(3.0)

    avg = load_outputs[LOAD_HORIZON_AVERAGE_MARGINAL_PRICE]
    assert avg.unit == "$/kWh"
    assert avg.type == OutputType.PRICE
    # Per-interval instantaneous $/kWh: equals dual[t] when energy[t] > 0,
    # 0 otherwise. State is the energy-weighted horizon average (2.10 / 7.0).
    assert tuple(avg.values) == pytest.approx((0.10, 0.20, 0.0, 0.40))
    assert avg.state == pytest.approx(2.10 / 7.0)


def test_next_24h_sensors_clip_to_first_24_hours() -> None:
    """Next-24h sensors include only the share of each step that lies within 24h."""
    adapter = LoadAdapter()
    # 30 hourly periods: first 24 in window, last 6 outside.
    n = 30
    power = (2.0,) * n
    dual = (0.10,) * n
    periods = (1.0,) * n

    result = adapter.outputs(
        "load",
        _outputs_with_dual(power=power, dual=dual, periods=periods),
        config=_config(n=n),
        periods=tuple(periods),
    )
    load_outputs = result[LOAD_DEVICE_LOAD]

    # 24 included steps * 2kW * 1h = 48 kWh total; cost = 24 * (2 kWh * 0.10)
    #   = 4.80 $ total; runtime = 24h; avg = 4.80 / 48 = 0.10 $/kWh.
    # Per-interval forecast carries the in-window contribution per step.
    daily_energy = load_outputs[LOAD_NEXT_24H_ENERGY]
    assert daily_energy.state == pytest.approx(48.0)
    # First 24 steps each contribute 2 kWh; last 6 contribute 0.
    assert tuple(daily_energy.values)[:24] == pytest.approx((2.0,) * 24)
    assert tuple(daily_energy.values)[24:] == pytest.approx((0.0,) * 6)

    daily_cost = load_outputs[LOAD_NEXT_24H_MARGINAL_COST]
    assert daily_cost.direction == "-"
    assert daily_cost.state == pytest.approx(4.80)
    assert tuple(daily_cost.values)[:24] == pytest.approx((0.20,) * 24)
    assert tuple(daily_cost.values)[24:] == pytest.approx((0.0,) * 6)

    daily_runtime = load_outputs[LOAD_NEXT_24H_RUNTIME]
    assert daily_runtime.state == pytest.approx(24.0)
    assert tuple(daily_runtime.values)[:24] == pytest.approx((1.0,) * 24)
    assert tuple(daily_runtime.values)[24:] == pytest.approx((0.0,) * 6)

    daily_avg = load_outputs[LOAD_NEXT_24H_AVERAGE_MARGINAL_PRICE]
    assert daily_avg.state == pytest.approx(0.10)
    # In-window steps publish the instantaneous $/kWh dual; out-of-window 0.
    assert tuple(daily_avg.values)[:24] == pytest.approx((0.10,) * 24)
    assert tuple(daily_avg.values)[24:] == pytest.approx((0.0,) * 6)


@pytest.mark.parametrize(
    ("power", "dual", "periods", "sheddable", "expected_states", "expected_values"),
    [
        pytest.param(
            (1.0,) * 60,
            (0.05,) * 60,
            (0.5,) * 60,
            True,
            # 48 steps of 1 kW * 0.5 h; cost is energy-weighted: 48 * 0.5 kWh * 0.05
            {LOAD_NEXT_24H_ENERGY: 24.0, LOAD_NEXT_24H_MARGINAL_COST: 1.20, LOAD_NEXT_24H_RUNTIME: 24.0},
            {},
            id="half_hour_periods_span_48_steps",
        ),
        pytest.param(
            (2.0, 3.0, 1.0),
            (0.10, 0.20, 0.05),
            (1.0, 1.0, 1.0),
            True,
            # Every step fits inside 24 h, so the next 24 h equals the horizon
            {
                LOAD_HORIZON_ENERGY: 6.0,
                LOAD_HORIZON_MARGINAL_COST: 0.85,
                LOAD_HORIZON_RUNTIME: 3.0,
                LOAD_NEXT_24H_ENERGY: 6.0,
                LOAD_NEXT_24H_MARGINAL_COST: 0.85,
                LOAD_NEXT_24H_RUNTIME: 3.0,
            },
            {},
            id="short_horizon_uses_all_periods",
        ),
        pytest.param(
            (1.0,) * 3,
            (0.10,) * 3,
            (20.0, 20.0, 20.0),
            True,
            # Steps end at 20 h, 40 h, 60 h: the second counts (24 - 20) / 20 = 0.2 of itself, the third none
            {
                LOAD_NEXT_24H_ENERGY: 24.0,
                LOAD_NEXT_24H_RUNTIME: 24.0,
                LOAD_NEXT_24H_MARGINAL_COST: 2.40,
                LOAD_NEXT_24H_AVERAGE_MARGINAL_PRICE: 0.10,
            },
            # Per step: all of the first, 0.2 of the second, none of the third
            {LOAD_NEXT_24H_ENERGY: (20.0, 4.0, 0.0), LOAD_NEXT_24H_RUNTIME: (20.0, 4.0, 0.0)},
            id="straddling_step_counts_its_in_window_fraction",
        ),
        pytest.param(
            (0.0, 0.0),
            (0.20, 0.30),
            (1.0, 1.0),
            True,
            {LOAD_HORIZON_AVERAGE_MARGINAL_PRICE: 0.0, LOAD_NEXT_24H_AVERAGE_MARGINAL_PRICE: 0.0},
            {LOAD_HORIZON_AVERAGE_MARGINAL_PRICE: (0.0, 0.0), LOAD_NEXT_24H_AVERAGE_MARGINAL_PRICE: (0.0, 0.0)},
            id="average_price_is_zero_without_energy",
        ),
        pytest.param(
            (1.0, 0.0, 1.0, 0.0),
            (0.10, 0.20, 0.10, 0.20),
            (0.25, 0.5, 1.0, 2.0),
            True,
            # Runtime sums only the periods where the load draws power
            {LOAD_HORIZON_RUNTIME: 1.25},
            {LOAD_HORIZON_RUNTIME: (0.25, 0.0, 1.0, 0.0)},
            id="runtime_excludes_shed_steps",
        ),
        pytest.param(
            (1.0, 2.0),
            (0.10, 0.20),
            (1.0, 1.0),
            False,
            {
                LOAD_HORIZON_MARGINAL_COST: 0.50,
                LOAD_HORIZON_ENERGY: 3.0,
                LOAD_HORIZON_AVERAGE_MARGINAL_PRICE: 0.50 / 3.0,
            },
            {LOAD_HORIZON_AVERAGE_MARGINAL_PRICE: (0.10, 0.20)},
            id="fixed_load_also_emits_stats",
        ),
    ],
)
def test_stats(
    power: tuple[float, ...],
    dual: tuple[float, ...],
    periods: tuple[float, ...],
    sheddable: bool,
    expected_states: Mapping[LoadOutputName, float],
    expected_values: Mapping[LoadOutputName, tuple[float, ...]],
) -> None:
    """Each statistics sensor carries its per-step values and its total over the horizon or the next 24 hours."""
    result = LoadAdapter().outputs(
        "load",
        _outputs_with_dual(power=power, dual=dual, periods=periods),
        config=_config(sheddable=sheddable, n=len(power)),
        periods=periods,
    )
    load_outputs = result[LOAD_DEVICE_LOAD]

    assert {name: load_outputs[name].state for name in expected_states} == pytest.approx(expected_states)
    assert {name: tuple(load_outputs[name].values) for name in expected_values} == pytest.approx(expected_values)


def test_stats_omitted_when_source_node_has_no_dual() -> None:
    """If the source node exposes no power-balance shadow, the stats outputs are not emitted.

    This keeps the adapter safe to use against unconstrained pass-through topologies, where
    publishing a misleading zero-cost figure would be worse than omitting the sensor.
    """
    adapter = LoadAdapter()
    model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]] = {
        "load:connection": {
            CONNECTION_POWER: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(1.0, 1.0), direction="+"),
        },
        # source node exists but has no element_power_balance entry
        "main_bus": {},
    }

    result = adapter.outputs("load", model_outputs, config=_config(n=2), periods=(1.0, 1.0))
    load_outputs = result[LOAD_DEVICE_LOAD]

    for missing in (
        LOAD_HORIZON_ENERGY,
        LOAD_HORIZON_MARGINAL_COST,
        LOAD_HORIZON_RUNTIME,
        LOAD_HORIZON_AVERAGE_MARGINAL_PRICE,
        LOAD_NEXT_24H_ENERGY,
        LOAD_NEXT_24H_MARGINAL_COST,
        LOAD_NEXT_24H_RUNTIME,
        LOAD_NEXT_24H_AVERAGE_MARGINAL_PRICE,
    ):
        assert missing not in load_outputs
