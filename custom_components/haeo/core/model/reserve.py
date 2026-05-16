"""Reserve power: ensure batteries hold enough energy to survive a blackout.

Computes per-period reserve requirements from the network's island loads
and generation, then constrains the battery group's stored energy to
cover the worst-case forward-looking net deficit.

Formulation:
    cum[t] = Σ_{k=0}^{t} net_demand[k]   (cumulative net demand)
    max_cum[t] ≥ max_cum[t-1]              (running max chain)
    max_cum[t] ≥ cum[t]
    reserve[t] = max_cum[N] - cum[t]       (full horizon)

    Σ_batteries stored_energy[t] x η ≥ reserve[t]

The running max chain tracks the peak cumulative deficit with O(n)
constraints. The undercharge pricing on the batteries provides the
cost incentive to maintain reserve.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


@dataclass
class ReserveConfig:
    """Configuration for a reserve power group."""

    island_load_power: dict[str, HighspyArray | NDArray[Any]]
    """Per-element arrays of non-discretionary load power (kW). LP variables for schedulable, constants for fixed."""

    island_gen_power: dict[str, HighspyArray | NDArray[Any]]
    """Per-element arrays of island generation power (kW). Typically solar forecast."""

    battery_stored_energy: dict[str, HighspyArray]
    """Per-battery stored energy variables (kWh). These are the cumulative energy variables from the Battery element."""

    battery_efficiency: dict[str, float]
    """Per-battery discharge path efficiency (0-1). Product of all segment efficiencies from battery to island loads."""

    battery_discharge_limit: dict[str, HighspyArray | NDArray[Any]]
    """Per-battery discharge power limit (kW). LP variables or constants."""

    periods: NDArray[np.floating[Any]]
    """Period durations in hours."""


@dataclass
class ReserveResult:
    """Result of adding reserve constraints to the LP."""

    reserve_requirement: HighspyArray
    """Per-period reserve requirement (kWh). LP variables."""

    max_cum_deficit: HighspyArray
    """Running maximum of cumulative net demand (kWh). LP variables."""

    cum_net_demand: list[Any]
    """Cumulative net demand at each period (kWh). LP expressions."""


def add_reserve_constraints(
    solver: Highs,
    config: ReserveConfig,
    *,
    name_prefix: str = "reserve",
) -> ReserveResult:
    """Add reserve power constraints to the LP.

    Creates:
    - Cumulative net demand tracking (expressions from island loads - gen)
    - Running max chain (O(n) constraints)
    - Reserve requirement = max_cum[N] - cum[t]
    - Battery group SOC floor: Σ stored x η ≥ reserve[t]

    Args:
        solver: HiGHS solver instance.
        config: Reserve configuration with island elements and batteries.
        name_prefix: Prefix for variable/constraint names.

    Returns:
        ReserveResult with the LP variables for post-solve extraction.

    """
    n = len(config.periods)
    dt = config.periods

    # Step 1: Compute net demand per period (load - generation) x Δt
    # This can be LP expressions if loads are schedulable
    net_demand: list[Any] = []
    for t in range(n):
        total_load: Any = 0.0
        for load_power in config.island_load_power.values():
            total_load = total_load + load_power[t]

        total_gen: Any = 0.0
        for gen_power in config.island_gen_power.values():
            total_gen = total_gen + gen_power[t]

        net_demand.append((total_load - total_gen) * float(dt[t]))

    # Step 2: Cumulative net demand
    cum: list[Any] = []
    running = 0.0
    for t in range(n):
        running = running + net_demand[t]
        cum.append(running)

    # Step 3: Running max chain — max_cum[t] tracks the maximum of cum[0..t]
    max_cum = solver.addVariables(
        n,
        lb=-1e20,
        name_prefix=f"{name_prefix}_maxcum_",
        out_array=True,
    )

    # max_cum[0] ≥ cum[0]
    solver.addConstr(max_cum[0] >= cum[0])

    for t in range(1, n):
        # max_cum[t] ≥ cum[t]
        solver.addConstr(max_cum[t] >= cum[t])
        # max_cum[t] ≥ max_cum[t-1] (monotonically non-decreasing)
        solver.addConstr(max_cum[t] >= max_cum[t - 1])

    # Step 4: Reserve requirement at each period
    # Reserve at t = final peak deficit minus cumulative demand before t
    # This is the remaining worst-case deficit from time t onwards.
    # At t=0, it's the full max deficit. At t=N-1, it's max_cum[N-1] - cum[N-1] ≥ 0.
    reserve = solver.addVariables(
        n,
        lb=0,
        name_prefix=f"{name_prefix}_req_",
        out_array=True,
    )

    # Use max_cum at the END of the horizon for full-horizon reserve
    final_max = max_cum[n - 1]

    for t in range(n):
        # Reserve equals final peak minus demand already served
        # cum_before[t] = cumulative net demand BEFORE period t starts
        cum_before = cum[t - 1] if t > 0 else 0.0
        solver.addConstr(reserve[t] >= final_max - cum_before)

    # Step 5: Battery group SOC floor
    # Σ_batteries stored_energy[t] x η ≥ reserve[t]
    for t in range(n):
        total_available: Any = 0.0
        for batt_name, stored in config.battery_stored_energy.items():
            eta = config.battery_efficiency.get(batt_name, 1.0)
            # stored[t+1] is the stored energy at the END of period t
            # (battery uses n+1 boundary values)
            total_available = total_available + stored[t + 1] * eta

        solver.addConstr(total_available >= reserve[t])

    # Step 6 (optional): Power constraint
    # Σ discharge_limits ≥ peak instantaneous load within window
    # For now, add per-period power constraint
    for t in range(n):
        total_discharge_power: Any = 0.0
        for discharge_lim in config.battery_discharge_limit.values():
            total_discharge_power = total_discharge_power + discharge_lim[t]

        total_load: Any = 0.0
        for load_power in config.island_load_power.values():
            total_load = total_load + load_power[t]

        # Power constraint: discharge capacity must cover instantaneous load
        if config.battery_discharge_limit:
            expr = total_discharge_power - total_load
            # Only add if this involves LP variables (not just constants)
            if hasattr(expr, "bounds") or not isinstance(expr, (int, float, np.floating)):
                solver.addConstr(total_discharge_power >= total_load)

    return ReserveResult(
        reserve_requirement=reserve,
        max_cum_deficit=max_cum,
        cum_net_demand=cum,
    )
