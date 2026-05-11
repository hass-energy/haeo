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
from typing import cast

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
    return cast(
        "LoadConfigData",
        {
            "element_type": ElementType.LOAD,
            "name": "load",
            "connection": as_connection_target(source),
            "forecast": {"forecast": np.array([1.0] * n)},
            "curtailment": {"curtailment": sheddable},
        },
    )


def _outputs_with_dual(
    *,
    power: tuple[float, ...],
    dual: tuple[float, ...],
    periods: tuple[float, ...],
    source: str = "main_bus",
) -> Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]:
    """Build a model_outputs mapping with a connection power output and a source node dual."""
    return cast(
        "Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]",
        {
            "load:connection": {
                CONNECTION_POWER: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=power, direction="+"),
            },
            source: {
                ELEMENT_POWER_BALANCE: OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=dual),
            },
        },
    )


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


def test_next_24h_window_with_30min_periods_picks_48_steps() -> None:
    """Half-hour periods: next 24h spans 48 steps exactly."""
    adapter = LoadAdapter()
    n = 60  # 30h horizon at 30-min steps
    power = (1.0,) * n
    dual = (0.05,) * n
    periods = (0.5,) * n

    result = adapter.outputs(
        "load",
        _outputs_with_dual(power=power, dual=dual, periods=periods),
        config=_config(n=n),
        periods=tuple(periods),
    )
    load_outputs = result[LOAD_DEVICE_LOAD]

    # 48 steps of (1kW * 0.5h) = 24 kWh total; cost = 48 * (0.5 kWh * 0.05) = 1.20 $.
    # NB: cost integration is energy-weighted ($/kWh dual), NOT power-weighted.
    assert load_outputs[LOAD_NEXT_24H_ENERGY].state == pytest.approx(24.0)
    assert load_outputs[LOAD_NEXT_24H_MARGINAL_COST].state == pytest.approx(1.20)
    assert load_outputs[LOAD_NEXT_24H_RUNTIME].state == pytest.approx(24.0)


def test_next_24h_window_with_short_horizon_uses_all_periods() -> None:
    """Horizon shorter than 24h: next-24h sensors equal horizon sensors."""
    adapter = LoadAdapter()
    power = (2.0, 3.0, 1.0)
    dual = (0.10, 0.20, 0.05)
    periods = (1.0, 1.0, 1.0)  # 3h total

    result = adapter.outputs(
        "load",
        _outputs_with_dual(power=power, dual=dual, periods=periods),
        config=_config(n=3),
        periods=tuple(periods),
    )
    load_outputs = result[LOAD_DEVICE_LOAD]

    # Horizon totals (state) and next-24h totals (state) must match when
    # every step fits inside the 24h window.
    horizon_energy_total = load_outputs[LOAD_HORIZON_ENERGY].state
    horizon_cost_total = load_outputs[LOAD_HORIZON_MARGINAL_COST].state
    horizon_runtime_total = load_outputs[LOAD_HORIZON_RUNTIME].state

    assert load_outputs[LOAD_NEXT_24H_ENERGY].state == pytest.approx(horizon_energy_total)
    assert load_outputs[LOAD_NEXT_24H_MARGINAL_COST].state == pytest.approx(horizon_cost_total)
    assert load_outputs[LOAD_NEXT_24H_RUNTIME].state == pytest.approx(horizon_runtime_total)


def test_next_24h_window_pro_rata_clips_straddling_step() -> None:
    """Boundary-straddling step contributes only its in-window fraction.

    Three 20h steps cover a 60h horizon:

    * step 0 starts at t=0h,  ends at t=20h: fraction = 1.0
    * step 1 starts at t=20h, ends at t=40h: fraction = (24-20)/20 = 0.2
    * step 2 starts at t=40h, ends at t=60h: fraction = 0.0

    With constant 1 kW power and 0.10 $/kWh dual:

    * energy:  1*1*20 + 0.2*1*20 + 0     = 24 kWh        (clips exactly)
    * runtime: 1*20   + 0.2*20    + 0    = 24 h          (clips exactly)
    * cost:    24 kWh * 0.10 $/kWh        = 2.40 $
    * avg:     2.40 / 24                  = 0.10 $/kWh

    Without pro-rata clipping the straddling step would be included whole,
    overstating energy and runtime by the leftover 16 h of that step.

    """
    adapter = LoadAdapter()
    n = 3
    power = (1.0,) * n
    dual = (0.10,) * n
    periods = (20.0, 20.0, 20.0)

    result = adapter.outputs(
        "load",
        _outputs_with_dual(power=power, dual=dual, periods=periods),
        config=_config(n=n),
        periods=tuple(periods),
    )
    load_outputs = result[LOAD_DEVICE_LOAD]

    assert load_outputs[LOAD_NEXT_24H_ENERGY].state == pytest.approx(24.0)
    assert load_outputs[LOAD_NEXT_24H_RUNTIME].state == pytest.approx(24.0)
    assert load_outputs[LOAD_NEXT_24H_MARGINAL_COST].state == pytest.approx(2.40)
    assert load_outputs[LOAD_NEXT_24H_AVERAGE_MARGINAL_PRICE].state == pytest.approx(0.10)


def test_average_cost_is_zero_when_energy_is_zero() -> None:
    """Average cost falls back to 0 (not a division-by-zero error) when no energy is consumed."""
    adapter = LoadAdapter()
    power = (0.0, 0.0)
    dual = (0.20, 0.30)
    periods = (1.0, 1.0)

    result = adapter.outputs(
        "load",
        _outputs_with_dual(power=power, dual=dual, periods=periods),
        config=_config(n=2),
        periods=tuple(periods),
    )
    load_outputs = result[LOAD_DEVICE_LOAD]

    assert load_outputs[LOAD_HORIZON_AVERAGE_MARGINAL_PRICE].state == pytest.approx(0.0)
    assert tuple(load_outputs[LOAD_HORIZON_AVERAGE_MARGINAL_PRICE].values) == pytest.approx((0.0, 0.0))
    assert load_outputs[LOAD_NEXT_24H_AVERAGE_MARGINAL_PRICE].state == pytest.approx(0.0)


def test_runtime_excludes_shed_timesteps() -> None:
    """Runtime is the sum of period durations for timesteps where power > 0."""
    adapter = LoadAdapter()
    power = (1.0, 0.0, 1.0, 0.0)
    dual = (0.10, 0.20, 0.10, 0.20)
    periods = (0.25, 0.5, 1.0, 2.0)

    result = adapter.outputs(
        "load",
        _outputs_with_dual(power=power, dual=dual, periods=periods),
        config=_config(n=4),
        periods=tuple(periods),
    )
    load_outputs = result[LOAD_DEVICE_LOAD]

    # Per-interval runtime: dt[t] when p[t] > 0 else 0. Sum = 1.25h.
    assert tuple(load_outputs[LOAD_HORIZON_RUNTIME].values) == pytest.approx((0.25, 0.0, 1.0, 0.0))
    assert load_outputs[LOAD_HORIZON_RUNTIME].state == pytest.approx(1.25)


def test_stats_omitted_when_source_node_has_no_dual() -> None:
    """If the source node exposes no power-balance shadow, the stats outputs are not emitted.

    This keeps the adapter safe to use against unconstrained pass-through topologies, where
    publishing a misleading zero-cost figure would be worse than omitting the sensor.
    """
    adapter = LoadAdapter()
    model_outputs = cast(
        "Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]",
        {
            "load:connection": {
                CONNECTION_POWER: OutputData(type=OutputType.POWER_FLOW, unit="kW", values=(1.0, 1.0), direction="+"),
            },
            # source node exists but has no element_power_balance entry
            "main_bus": {},
        },
    )

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


def test_fixed_load_also_emits_stats_when_source_dual_is_present() -> None:
    """Stats sensors are emitted for fixed loads too (cost is well-defined either way)."""
    adapter = LoadAdapter()
    power = (1.0, 2.0)
    dual = (0.10, 0.20)
    periods = (1.0, 1.0)

    result = adapter.outputs(
        "load",
        _outputs_with_dual(power=power, dual=dual, periods=periods),
        config=_config(sheddable=False, n=2),
        periods=tuple(periods),
    )
    load_outputs = result[LOAD_DEVICE_LOAD]

    # Cost: 1*0.10 + 2*0.20 = 0.50; energy: 3 kWh; avg: 0.50/3
    assert load_outputs[LOAD_HORIZON_MARGINAL_COST].state == pytest.approx(0.50)
    assert load_outputs[LOAD_HORIZON_ENERGY].state == pytest.approx(3.0)
    assert load_outputs[LOAD_HORIZON_AVERAGE_MARGINAL_PRICE].state == pytest.approx(0.50 / 3.0)
