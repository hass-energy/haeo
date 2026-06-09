"""Load element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

import numpy as np

from custom_components.haeo.core.adapters.output_utils import (
    connection_power,
    expect_output_data,
    marginal_balance_dual_per_step,
    split_balance_shadow_rows,
)
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
        **_kwargs: Any,
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
            load_outputs[LOAD_FORECAST_LIMIT_PRICE] = replace(shadow, advanced=True)

        # Horizon + next-24h statistics. Cost uses incremental marginal pricing:
        # energy[t] * lambda_marginal[t], where lambda_marginal is the cheapest source-node
        # balance dual among VLAN tags with ranging headroom.
        source_name = extract_connection_target(config[CONF_CONNECTION])
        if len(periods) > 0 and connection is not None:
            cost_per_step = _marginal_cost_per_step(connection, model_outputs, source_name, len(periods), periods)
            if cost_per_step is not None:
                load_outputs.update(_stats_outputs(power.values, cost_per_step, periods))

        return {LOAD_DEVICE_LOAD: load_outputs}


def _marginal_cost_per_step(
    connection: Mapping[ModelOutputName, ModelOutputValue],
    model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
    source_name: str,
    n_periods: int,
    periods: Sequence[float],
) -> np.ndarray | None:
    """Return per-timestep incremental marginal cost ($) from load energy and source duals."""
    source_outputs = model_outputs.get(source_name)
    if source_outputs is None:
        return None
    dual = expect_output_data(source_outputs.get(ELEMENT_POWER_BALANCE))
    if dual is None:
        return None

    split = split_balance_shadow_rows(dual, n_periods)
    if split is None:
        return None
    duals_by_tag, range_up_by_tag = split
    marginal_dual = marginal_balance_dual_per_step(duals_by_tag, range_up_by_tag)

    power = expect_output_data(connection.get(CONNECTION_POWER))
    if power is None:
        return None
    power_values = np.asarray(power.values, dtype=float)
    if len(power_values) != n_periods:
        return None
    return power_values * np.asarray(periods, dtype=float) * marginal_dual


def _stats_outputs(
    power: Sequence[float],
    cost_per_step: np.ndarray,
    periods: Sequence[float],
) -> dict[LoadOutputName, OutputData]:
    """Build the 8 full-horizon + next-24h statistics outputs.

    Cost is ``cost[t] = energy[t] * lambda_marginal[t]`` ($), where ``lambda_marginal`` is
    the cheapest source-node balance dual among VLAN tags with ranging headroom.
    When all tags are saturated, the most expensive dual is used. Single-tag
    networks use the flat balance dual directly.

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
    power_arr = np.asarray(power, dtype=float)
    periods_arr = np.asarray(periods, dtype=float)
    cost_arr = np.asarray(cost_per_step, dtype=float)

    energy_per_step = power_arr * periods_arr
    runtime_per_step = np.where(np.abs(power_arr) > _RUNTIME_POWER_EPS, periods_arr, 0.0)

    horizon_energy = float(energy_per_step.sum())
    horizon_cost = float(cost_arr.sum())
    horizon_runtime = float(runtime_per_step.sum())
    horizon_avg_cost = _weighted_average(cost_per_step, energy_per_step)

    avg_cost_per_step = _weighted_average_per_step(cost_arr, energy_per_step)

    fractions = _next_24h_window_fractions(periods_arr)
    energy_24h_per_step = energy_per_step * fractions
    cost_24h_per_step = cost_arr * fractions
    runtime_24h_per_step = runtime_per_step * fractions

    next_24h_energy = float(energy_24h_per_step.sum())
    next_24h_cost = float(cost_24h_per_step.sum())
    next_24h_runtime = float(runtime_24h_per_step.sum())
    next_24h_avg_cost = _weighted_average(cost_24h_per_step, energy_24h_per_step)
    avg_cost_24h_per_step = _weighted_average_per_step(cost_24h_per_step, energy_24h_per_step)

    return {
        LOAD_HORIZON_ENERGY: OutputData(
            type=OutputType.ENERGY, unit="kWh", values=energy_per_step, state=horizon_energy, advanced=True
        ),
        LOAD_HORIZON_MARGINAL_COST: OutputData(
            type=OutputType.COST,
            unit="$",
            values=cost_arr,
            direction="-",
            state=horizon_cost,
            display_precision=2,
            advanced=True,
        ),
        LOAD_HORIZON_RUNTIME: OutputData(
            type=OutputType.DURATION, unit="h", values=runtime_per_step, state=horizon_runtime, advanced=True
        ),
        LOAD_HORIZON_AVERAGE_MARGINAL_PRICE: OutputData(
            type=OutputType.PRICE,
            unit="$/kWh",
            values=avg_cost_per_step,
            state=horizon_avg_cost,
            display_precision=2,
            advanced=True,
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
            type=OutputType.DURATION,
            unit="h",
            values=runtime_24h_per_step,
            state=next_24h_runtime,
            advanced=True,
        ),
        LOAD_NEXT_24H_AVERAGE_MARGINAL_PRICE: OutputData(
            type=OutputType.PRICE,
            unit="$/kWh",
            values=avg_cost_24h_per_step,
            state=next_24h_avg_cost,
            display_precision=2,
            advanced=True,
        ),
    }


def _weighted_average(numerator: np.ndarray, denominator: np.ndarray) -> float:
    """Return energy-weighted average, or 0.0 when total energy is non-positive."""
    total_energy = float(denominator.sum())
    if total_energy <= 0:
        return 0.0
    return float(numerator.sum()) / total_energy


def _weighted_average_per_step(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    """Return per-step ratio with zero where denominator is non-positive."""
    return np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)


def _next_24h_window_fractions(periods: np.ndarray) -> np.ndarray:
    """Return the per-timestep inclusion fraction for the next-24h window.

    Each timestep is assigned a fraction in [0.0, 1.0] equal to the share of
    its duration that falls within the first ``_NEXT_24H_WINDOW_HOURS`` of
    the horizon. Steps that start at or after the boundary contribute 0.0;
    steps that finish at or before the boundary contribute 1.0; the
    boundary-straddling step contributes the partial fraction so aggregates
    multiplied by these fractions clip exactly to 24h.

    """
    ends = np.cumsum(periods)
    starts = ends - periods
    return np.clip(
        np.divide(
            _NEXT_24H_WINDOW_HOURS - starts,
            periods,
            out=np.zeros_like(periods),
            where=periods > 0,
        ),
        0.0,
        1.0,
    )


adapter = LoadAdapter()
