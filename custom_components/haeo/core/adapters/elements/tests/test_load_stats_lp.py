"""LP-level integration tests for the load cumulative + rolling-24h sensors.

Build small grid+load networks, solve the LP, push the resulting model outputs
through ``LoadAdapter.outputs``, and verify the published statistics agree with
the analytic per-timestep integrals. This guards against unit-of-measure
regressions (e.g. forgetting that ``element_power_balance`` shadows are already
period-integrated) and ensures the rolling-24h window keeps its semantics when
fed real solver output.
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
from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.adapters.policy_compilation import compile_policies
from custom_components.haeo.core.adapters.registry import collect_model_elements
from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER
from custom_components.haeo.core.model.network import Network
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.grid import GridConfigData
from custom_components.haeo.core.schema.elements.load import LoadConfigData

_LOAD_FORECAST = 5.0  # kW
_THRESHOLD_PRICE = 0.30  # $/kWh — keeps the load on for cheap periods, sheds when expensive
# Hourly prices: cheap, cheap, expensive, expensive
_IMPORT_PRICES = np.array([0.20, 0.25, 0.35, 0.40])
_PERIODS_HOURS = np.array([1.0, 1.0, 1.0, 1.0])


def _make_grid_config() -> GridConfigData:
    return cast(
        "GridConfigData",
        {
            "element_type": ElementType.GRID,
            "name": "grid",
            "connection": as_connection_target("main_bus"),
            "pricing": {
                "price_source_target": _IMPORT_PRICES,
                "price_target_source": np.array([0.0] * 4),
            },
            "power_limits": {},
        },
    )


def _make_load_config(threshold_price: float | None = _THRESHOLD_PRICE) -> LoadConfigData:
    config: LoadConfigData = cast(
        "LoadConfigData",
        {
            "element_type": ElementType.LOAD,
            "name": "load",
            "connection": as_connection_target("main_bus"),
            "forecast": {"forecast": np.array([_LOAD_FORECAST] * 4)},
            "curtailment": {"curtailment": True},
        },
    )
    if threshold_price is not None:
        config["threshold"] = {"threshold_price": threshold_price}
    return config


def _solve_network(
    grid_config: GridConfigData,
    load_config: LoadConfigData,
    *,
    bus_is_source: bool = False,
    bus_is_sink: bool = False,
    periods: np.ndarray | None = None,
) -> Network:
    net = Network(name="stats-lp-test", periods=periods if periods is not None else _PERIODS_HOURS)
    participants = {"grid": grid_config, "load": load_config}
    net.add(
        {
            "element_type": "node",
            "name": "main_bus",
            "is_source": bus_is_source,
            "is_sink": bus_is_sink,
        }
    )
    sorted_model_elements = list(collect_model_elements(participants))  # type: ignore[arg-type]
    # Compile policies (empty rule list) so connections receive default tags.
    result = compile_policies(sorted_model_elements, [])
    for cfg in result["elements"]:
        net.add(cfg)
    net.optimize()
    return net


def _model_outputs(net: Network) -> Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]:
    return cast(
        "Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]",
        {element_name: element.outputs() for element_name, element in net.elements.items()},
    )


def test_total_cost_matches_energy_times_node_dual_integral() -> None:
    """Verify ``total_cost = sum(energy[t] * node_dual[t])`` and energy/runtime match dispatch.

    With grid prices [0.20, 0.25, 0.35, 0.40] and a threshold of $0.30/kWh, the LP
    serves the 5kW load in the first two cheap periods and sheds in the last two.
    The published cost must match the energy-weighted integral of the source-node
    shadow price (which is in $/kWh), and should sit close to (but not necessarily
    equal to) the price-only estimate because the dual also reflects HAEO's
    secondary regularizer terms.
    """
    net = _solve_network(_make_grid_config(), _make_load_config())
    adapter = LoadAdapter()
    model_outputs = _model_outputs(net)

    # Pull the raw p_load and main_bus dual the adapter uses internally.
    p_load = tuple(float(v) for v in expect_output_data(model_outputs["load:connection"][CONNECTION_POWER]).values)
    main_bus_dual = tuple(float(v) for v in expect_output_data(model_outputs["main_bus"][ELEMENT_POWER_BALANCE]).values)
    energy_per_step = tuple(p * dt for p, dt in zip(p_load, _PERIODS_HOURS, strict=True))
    expected_cost = sum(e * d for e, d in zip(energy_per_step, main_bus_dual, strict=True))
    expected_energy = sum(energy_per_step)
    expected_runtime = sum(dt for p, dt in zip(p_load, _PERIODS_HOURS, strict=True) if abs(p) > 1e-9)

    outputs = adapter.outputs(
        "load",
        model_outputs,
        config=_make_load_config(),
        periods=_PERIODS_HOURS,
    )[LOAD_DEVICE_LOAD]

    assert outputs[LOAD_HORIZON_ENERGY].state == pytest.approx(expected_energy, abs=1e-6)
    assert outputs[LOAD_HORIZON_MARGINAL_COST].state == pytest.approx(expected_cost, abs=1e-6)
    assert outputs[LOAD_HORIZON_RUNTIME].state == pytest.approx(expected_runtime, abs=1e-6)
    assert outputs[LOAD_HORIZON_AVERAGE_MARGINAL_PRICE].state == pytest.approx(
        expected_cost / expected_energy, abs=1e-6
    )

    # Sanity: dispatch should be 5kW in the two cheap periods, ~0 elsewhere; cost
    # should land near the price-only estimate (2.25 $) with regularizer-driven slack.
    assert p_load[0] == pytest.approx(_LOAD_FORECAST, abs=1e-6)
    assert p_load[1] == pytest.approx(_LOAD_FORECAST, abs=1e-6)
    assert p_load[2] == pytest.approx(0.0, abs=1e-6)
    assert p_load[3] == pytest.approx(0.0, abs=1e-6)
    assert expected_runtime == pytest.approx(2.0, abs=1e-6)
    price_only_estimate = _LOAD_FORECAST * (_IMPORT_PRICES[0] + _IMPORT_PRICES[1])
    assert expected_cost == pytest.approx(price_only_estimate, rel=0.05)


def test_daily_sensors_match_totals_when_horizon_is_under_24h() -> None:
    """Horizon of 4h <= 24h, so daily window covers every timestep."""
    net = _solve_network(_make_grid_config(), _make_load_config())
    adapter = LoadAdapter()

    outputs = adapter.outputs(
        "load",
        _model_outputs(net),
        config=_make_load_config(),
        periods=_PERIODS_HOURS,
    )[LOAD_DEVICE_LOAD]

    assert outputs[LOAD_NEXT_24H_ENERGY].state == pytest.approx(outputs[LOAD_HORIZON_ENERGY].state, abs=1e-6)
    assert outputs[LOAD_NEXT_24H_MARGINAL_COST].state == pytest.approx(
        outputs[LOAD_HORIZON_MARGINAL_COST].state, abs=1e-6
    )
    assert outputs[LOAD_NEXT_24H_RUNTIME].state == pytest.approx(outputs[LOAD_HORIZON_RUNTIME].state, abs=1e-6)
    assert outputs[LOAD_NEXT_24H_AVERAGE_MARGINAL_PRICE].state == pytest.approx(
        outputs[LOAD_HORIZON_AVERAGE_MARGINAL_PRICE].state, abs=1e-6
    )


def test_stats_outputs_present_when_bus_is_source_and_sink() -> None:
    """Regression: stats sensors survive a multi-block dual on a source+sink bus.

    When the source node is is_source=is_sink=True (HA default for a switchboard),
    ``element_power_balance`` returns a multi-block dual vector after PR #426. The
    adapter must still surface the 8 stats sensors (energy/cost/runtime/average
    cost, total + daily), not silently drop them on length mismatch.
    """
    net = _solve_network(_make_grid_config(), _make_load_config(), bus_is_source=True, bus_is_sink=True)
    adapter = LoadAdapter()

    outputs = adapter.outputs(
        "load",
        _model_outputs(net),
        config=_make_load_config(),
        periods=_PERIODS_HOURS,
    )[LOAD_DEVICE_LOAD]

    for sensor in (
        LOAD_HORIZON_ENERGY,
        LOAD_HORIZON_MARGINAL_COST,
        LOAD_HORIZON_RUNTIME,
        LOAD_HORIZON_AVERAGE_MARGINAL_PRICE,
        LOAD_NEXT_24H_ENERGY,
        LOAD_NEXT_24H_MARGINAL_COST,
        LOAD_NEXT_24H_RUNTIME,
        LOAD_NEXT_24H_AVERAGE_MARGINAL_PRICE,
    ):
        assert sensor in outputs, f"{sensor} missing from load outputs for source+sink bus"


def test_cost_integration_uses_energy_not_power_on_sub_hour_periods() -> None:
    """Regression: ``cost[t] = energy[t] * node_dual[t]`` (NOT ``power[t] * dual``).

    HAEO horizons mix 1-60 min intervals. The source-node ``element_power_balance``
    dual is in $/kWh (the LP balance is formulated in energy units), so cost
    must be the energy-weighted integral. Multiplying by power instead of energy
    is off by ``1/periods[t]`` per step -- for a 5-min period it overstates cost
    by 12x, which is what surfaced as a daily-average-cost of ~$1/kWh on a
    threshold-limited $0.15/kWh miner load.
    """
    # 4 timesteps at 15 minutes each (0.25 h) so the bug, if present, scales cost by 4x.
    sub_hour_periods = np.array([0.25, 0.25, 0.25, 0.25])
    grid_config = _make_grid_config()
    load_config = _make_load_config()

    net = _solve_network(grid_config, load_config, periods=sub_hour_periods)
    adapter = LoadAdapter()
    model_outputs = _model_outputs(net)

    p_load = tuple(float(v) for v in expect_output_data(model_outputs["load:connection"][CONNECTION_POWER]).values)
    main_bus_dual = tuple(float(v) for v in expect_output_data(model_outputs["main_bus"][ELEMENT_POWER_BALANCE]).values)
    energy_per_step = tuple(p * dt for p, dt in zip(p_load, sub_hour_periods, strict=True))
    expected_cost_energy_weighted = sum(e * d for e, d in zip(energy_per_step, main_bus_dual, strict=True))
    expected_cost_power_only = sum(p * d for p, d in zip(p_load, main_bus_dual, strict=True))

    outputs = adapter.outputs(
        "load",
        model_outputs,
        config=load_config,
        periods=sub_hour_periods,
    )[LOAD_DEVICE_LOAD]

    # The published cost must equal the energy-weighted integral, not the
    # period-naive power*dual sum the prior implementation produced.
    assert outputs[LOAD_HORIZON_MARGINAL_COST].state == pytest.approx(expected_cost_energy_weighted, abs=1e-6)
    # And on a sub-hour horizon the two formulas differ by 1/periods[t] = 4x;
    # assert this divergence so the test fails loudly if the regression returns.
    if abs(expected_cost_energy_weighted) > 1e-9:
        ratio = expected_cost_power_only / expected_cost_energy_weighted
        assert ratio == pytest.approx(1.0 / sub_hour_periods[0], abs=1e-3), (
            f"Sanity: power*dual should be {1.0 / sub_hour_periods[0]}x the energy*dual "
            f"integral on a {sub_hour_periods[0]}h horizon; got ratio={ratio}."
        )

    # Average cost must remain on the same order as the import prices ($/kWh),
    # NOT inflated by the period factor.
    avg_cost = outputs[LOAD_HORIZON_AVERAGE_MARGINAL_PRICE].state
    assert avg_cost is not None
    assert 0.0 <= float(avg_cost) <= max(_IMPORT_PRICES) + 0.05, (
        f"total_average_cost={avg_cost} $/kWh is outside the plausible price band; "
        f"this indicates the cost integration is missing the periods[t] factor."
    )


def test_zero_dispatch_produces_zero_stats_and_zero_average_cost() -> None:
    """When the LP sheds the load entirely, runtime/energy/cost are 0 and avg-cost is 0 (not NaN)."""
    # Use a threshold below every grid price → LP sheds entirely
    grid_config = _make_grid_config()
    load_config = _make_load_config(threshold_price=0.05)
    net = _solve_network(grid_config, load_config)
    adapter = LoadAdapter()

    outputs = adapter.outputs(
        "load",
        _model_outputs(net),
        config=load_config,
        periods=_PERIODS_HOURS,
    )[LOAD_DEVICE_LOAD]

    assert outputs[LOAD_HORIZON_ENERGY].state == pytest.approx(0.0, abs=1e-6)
    assert outputs[LOAD_HORIZON_MARGINAL_COST].state == pytest.approx(0.0, abs=1e-6)
    assert outputs[LOAD_HORIZON_RUNTIME].state == pytest.approx(0.0, abs=1e-6)
    assert outputs[LOAD_HORIZON_AVERAGE_MARGINAL_PRICE].state == pytest.approx(0.0, abs=1e-6)
