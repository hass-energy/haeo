"""Load element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Final, Literal

import numpy as np

from custom_components.haeo.core.adapters.output_utils import connection_power, expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER, CONNECTION_SEGMENTS
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.load import ELEMENT_TYPE, LoadConfigData
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
)

# Load output names
type LoadOutputName = Literal[
    "load_power",
    "load_forecast_limit_price",
    "load_horizon_energy",
    "load_horizon_marginal_cost",
    "load_horizon_runtime",
    "load_horizon_average_marginal_price",
    "load_next_24h_energy",
    "load_next_24h_marginal_cost",
    "load_next_24h_runtime",
    "load_next_24h_average_marginal_price",
]

LOAD_OUTPUT_NAMES: Final[frozenset[LoadOutputName]] = frozenset(
    (
        LOAD_POWER := "load_power",
        # Shadow price
        LOAD_FORECAST_LIMIT_PRICE := "load_forecast_limit_price",
        # Full-horizon statistics (over the entire optimization horizon)
        LOAD_HORIZON_ENERGY := "load_horizon_energy",
        LOAD_HORIZON_MARGINAL_COST := "load_horizon_marginal_cost",
        LOAD_HORIZON_RUNTIME := "load_horizon_runtime",
        LOAD_HORIZON_AVERAGE_MARGINAL_PRICE := "load_horizon_average_marginal_price",
        # Next-24h-forward statistics, pro-rata clipped at the 24h boundary
        LOAD_NEXT_24H_ENERGY := "load_next_24h_energy",
        LOAD_NEXT_24H_MARGINAL_COST := "load_next_24h_marginal_cost",
        LOAD_NEXT_24H_RUNTIME := "load_next_24h_runtime",
        LOAD_NEXT_24H_AVERAGE_MARGINAL_PRICE := "load_next_24h_average_marginal_price",
    )
)

# Forward-looking window length for the "next 24h" sensors (hours, from horizon start)
_NEXT_24H_WINDOW_HOURS: Final[float] = 24.0
# Power threshold below which a timestep is considered "shed" (not running), in kW.
# Small but non-zero to ignore floating-point noise from the LP solver.
_RUNTIME_POWER_EPS: Final[float] = 1e-9

type LoadDeviceName = Literal[ElementType.LOAD]

LOAD_DEVICE_NAMES: Final[frozenset[LoadDeviceName]] = frozenset(
    (LOAD_DEVICE_LOAD := ElementType.LOAD,),
)


class LoadAdapter:
    """Adapter for Load elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED
    can_source: bool = False
    can_sink: bool = True

    def model_elements(self, config: LoadConfigData) -> list[ModelElementConfig]:
        """Create model elements for Load configuration."""
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": config["name"],
                "is_source": False,
                "is_sink": True,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config['name']}:connection",
                "source": extract_connection_target(config[CONF_CONNECTION]),
                "target": config["name"],
                "is_time_sensitive": True,
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power": config[SECTION_FORECAST][CONF_FORECAST],
                        "fixed": not config[SECTION_CURTAILMENT].get(CONF_CURTAILMENT, False),
                    },
                },
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        *,
        config: LoadConfigData,
        periods: Sequence[float] = (),
        **_kwargs: object,
    ) -> Mapping[LoadDeviceName, Mapping[LoadOutputName, OutputData]]:
        """Map model outputs to load-specific output names."""
        connection = model_outputs.get(f"{name}:connection")
        fixed = not config[SECTION_CURTAILMENT].get(CONF_CURTAILMENT, False)
        forecast = config[SECTION_FORECAST][CONF_FORECAST]
        if connection is not None:
            period_count = len(expect_output_data(connection[CONNECTION_POWER]).values)
        else:
            period_count = int(np.atleast_1d(forecast).size)

        power = connection_power(connection, period_count)
        load_outputs: dict[LoadOutputName, OutputData] = {
            LOAD_POWER: replace(power, type=OutputType.POWER, direction="-", fixed=fixed),
        }

        # Shadow price from power_limit segment (if present)
        if (
            connection is not None
            and isinstance(segments_output := connection.get(CONNECTION_SEGMENTS), Mapping)
            and isinstance(power_limit_outputs := segments_output.get("power_limit"), Mapping)
            and (shadow := expect_output_data(power_limit_outputs.get("power_limit"))) is not None
        ):
            load_outputs[LOAD_FORECAST_LIMIT_PRICE] = shadow

        # Cumulative + rolling-24h statistics. Marginal cost uses the source-node
        # power-balance shadow price (node_dual, $/kWh, already period-integrated)
        # so that cost = energy * node_dual is in $.
        source_name = extract_connection_target(config[CONF_CONNECTION])
        node_dual = _node_dual_values(model_outputs, source_name, len(periods)) if len(periods) > 0 else None
        if node_dual is not None:
            power_values = tuple(float(v) for v in power.values)
            period_values = tuple(float(v) for v in periods)
            load_outputs.update(_stats_outputs(power_values, node_dual, period_values))

        return {LOAD_DEVICE_LOAD: load_outputs}


def _node_dual_values(
    model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
    source_name: str,
    n_periods: int,
) -> tuple[float, ...] | None:
    """Return the source-node power-balance shadow price ($/kWh).

    Uses the first ``n_periods`` of ``element_power_balance``: the same series
    that the node's canonical ``node_power_balance`` sensor exposes in Home
    Assistant (the coordinator zips values with ``n_periods+1`` timestamps
    using ``strict=False``, so trailing tag-balance / decomposition blocks are
    already dropped from the published forecast). Multiplying load energy
    (``power * dt``) by this $/kWh price gives the per-step cost in dollars.

    Since PR #426 (DEFAULT_TAG removal), ``element_power_balance`` is a flat
    list of per-period constraints. For a multi-tag node the layout is
    ``[optional production-decomp block, optional consumption-decomp block,
    one per-tag balance block per tag]``, each of length ``n_periods``. The
    first block always carries a balance dual whose magnitude matches the
    user-visible switchboard shadow price, which is the correct marginal
    cost for an additional unit of load energy at this node.

    Returns None when the source node has no ``element_power_balance`` output
    (e.g. unconstrained pass-through nodes) or when the dual length is not a
    whole multiple of ``n_periods`` (defensive: would indicate a layout bug).
    """
    source_outputs = model_outputs.get(source_name)
    if source_outputs is None:
        return None
    dual = expect_output_data(source_outputs.get(ELEMENT_POWER_BALANCE))
    if dual is None:
        return None
    values = tuple(float(v) for v in dual.values)
    if len(values) == 0 or len(values) % n_periods != 0:
        return None
    return values[:n_periods]


def _stats_outputs(
    power: Sequence[float],
    node_dual: Sequence[float],
    periods: Sequence[float],
) -> dict[LoadOutputName, OutputData]:
    """Build the 8 full-horizon + next-24h statistics outputs.

    Cost is integrated as ``cost[t] = power[t] * periods[t] * node_dual[t]``
    ($) where ``node_dual[t]`` is the source-node power-balance shadow price
    in $/kWh (see ``Node.element_power_balance``: the LP balance is
    formulated in energy units so the dual is independent of period width).
    The ``power * periods`` factor is the per-step energy in kWh, so cost is
    ``energy[t] * node_dual[t]`` and totals are correct for variable-width
    horizons (1-60 min periods).

    Energy is ``power[t] * periods[t]`` (kWh) and runtime is ``periods[t]``
    for timesteps where ``power[t] > _RUNTIME_POWER_EPS`` (h).

    The forecast attribute on every stats sensor exposes the **per-interval**
    series (cost / energy / runtime / instantaneous average cost) so that the
    forecast card and history charts show the contribution of each timestep
    rather than a flat repeated total. The scalar state reported by each
    sensor is set via ``OutputData.state``:
      * horizon_* sensors -> sum across the entire horizon
      * next_24h_* sensors -> sum across the first ``_NEXT_24H_WINDOW_HOURS``,
        with the boundary-straddling step pro-rated.
    Average cost is energy-weighted (``total_cost / total_energy``, $/kWh)
    and falls back to 0.0 when the corresponding energy total is non-positive.

    """
    energy_per_step = tuple(p * dt for p, dt in zip(power, periods, strict=True))
    cost_per_step = tuple(e * d for e, d in zip(energy_per_step, node_dual, strict=True))
    runtime_per_step = tuple(dt if abs(p) > _RUNTIME_POWER_EPS else 0.0 for p, dt in zip(power, periods, strict=True))

    # Horizon totals (full-horizon sum across every step).
    horizon_energy = sum(energy_per_step)
    horizon_cost = sum(cost_per_step)
    horizon_runtime = sum(runtime_per_step)
    horizon_avg_cost = _safe_divide(horizon_cost, horizon_energy)

    # Per-interval instantaneous average cost: equals node_dual[t] whenever
    # energy[t] > 0 (cost[t] / energy[t] = node_dual[t]) and 0 elsewhere.
    # Exposed as the forecast attribute so the chart shows the marginal
    # $/kWh price applied to each active step.
    avg_cost_per_step = tuple(_safe_divide(c, e) for c, e in zip(cost_per_step, energy_per_step, strict=True))

    # Next-24h-forward window starting from t=0 (the present): each timestep
    # contributes a fraction in [0.0, 1.0] of its duration that lies inside
    # _NEXT_24H_WINDOW_HOURS. Steps fully outside contribute 0.0; steps fully
    # inside contribute 1.0; the straddling step contributes the partial
    # fraction so totals clip exactly to 24h. The same fractions weight the
    # per-step forecast values so steps beyond 24h appear as 0 in the chart.
    fractions = _next_24h_window_fractions(periods)
    energy_24h_per_step = tuple(e * f for e, f in zip(energy_per_step, fractions, strict=True))
    cost_24h_per_step = tuple(c * f for c, f in zip(cost_per_step, fractions, strict=True))
    runtime_24h_per_step = tuple(r * f for r, f in zip(runtime_per_step, fractions, strict=True))
    next_24h_energy = sum(energy_24h_per_step)
    next_24h_cost = sum(cost_24h_per_step)
    next_24h_runtime = sum(runtime_24h_per_step)
    next_24h_avg_cost = _safe_divide(next_24h_cost, next_24h_energy)
    # Per-step instantaneous $/kWh inside the 24h window, 0 outside.
    avg_cost_24h_per_step = tuple(
        _safe_divide(c, e) if e > 0 else 0.0 for c, e in zip(cost_24h_per_step, energy_24h_per_step, strict=True)
    )

    return {
        LOAD_HORIZON_ENERGY: OutputData(
            type=OutputType.ENERGY, unit="kWh", values=energy_per_step, state=horizon_energy
        ),
        LOAD_HORIZON_MARGINAL_COST: OutputData(
            type=OutputType.COST,
            unit="$",
            values=cost_per_step,
            direction="-",
            state=horizon_cost,
            display_precision=2,
        ),
        LOAD_HORIZON_RUNTIME: OutputData(
            type=OutputType.DURATION, unit="h", values=runtime_per_step, state=horizon_runtime
        ),
        LOAD_HORIZON_AVERAGE_MARGINAL_PRICE: OutputData(
            type=OutputType.PRICE,
            unit="$/kWh",
            values=avg_cost_per_step,
            state=horizon_avg_cost,
            display_precision=2,
        ),
        LOAD_NEXT_24H_ENERGY: OutputData(
            type=OutputType.ENERGY, unit="kWh", values=energy_24h_per_step, state=next_24h_energy
        ),
        LOAD_NEXT_24H_MARGINAL_COST: OutputData(
            type=OutputType.COST,
            unit="$",
            values=cost_24h_per_step,
            direction="-",
            state=next_24h_cost,
            display_precision=2,
        ),
        LOAD_NEXT_24H_RUNTIME: OutputData(
            type=OutputType.DURATION, unit="h", values=runtime_24h_per_step, state=next_24h_runtime
        ),
        LOAD_NEXT_24H_AVERAGE_MARGINAL_PRICE: OutputData(
            type=OutputType.PRICE,
            unit="$/kWh",
            values=avg_cost_24h_per_step,
            state=next_24h_avg_cost,
            display_precision=2,
        ),
    }


def _safe_divide(numerator: float, denominator: float) -> float:
    """Divide ``numerator`` by ``denominator``, returning 0.0 when denominator is non-positive."""
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _next_24h_window_fractions(periods: Sequence[float]) -> tuple[float, ...]:
    """Return the per-timestep inclusion fraction for the next-24h window.

    Each timestep is assigned a fraction in [0.0, 1.0] equal to the share of
    its duration that falls within the first ``_NEXT_24H_WINDOW_HOURS`` of
    the horizon. Steps that start at or after the boundary contribute 0.0;
    steps that finish at or before the boundary contribute 1.0; the
    boundary-straddling step contributes the partial fraction so aggregates
    multiplied by these fractions clip exactly to 24h.

    """
    fractions: list[float] = []
    elapsed = 0.0
    for dt in periods:
        remaining = _NEXT_24H_WINDOW_HOURS - elapsed
        if remaining <= 0.0 or dt <= 0.0:
            fractions.append(0.0)
        elif remaining >= dt:
            fractions.append(1.0)
        else:
            fractions.append(remaining / dt)
        elapsed += dt
    return tuple(fractions)


adapter = LoadAdapter()
