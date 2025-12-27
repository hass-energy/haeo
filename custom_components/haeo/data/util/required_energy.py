"""Calculate required energy using maximum drawdown algorithm."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from custom_components.haeo.elements import ELEMENT_TYPE_LOAD, ELEMENT_TYPE_SOLAR, ElementConfigData


@dataclass
class RequiredEnergyResult:
    """Result of required energy calculation."""

    required_energy: list[float]  # kWh at each timestep boundary (n_periods + 1)
    net_power: list[float]  # kW for each period (n_periods), positive = surplus, negative = deficit


def calculate_required_energy(
    elements: Mapping[str, ElementConfigData],
    periods_hours: Sequence[float],
    max_horizon_hours: float | None = None,
) -> RequiredEnergyResult:
    """Calculate the required energy at each timestep using maximum drawdown.

    The required energy represents the minimum energy needed (e.g. battery storage) at each
    timestep to remain self-sufficient for a configurable duration.

    Given a typical grid-connected solar + battery system, energy will have to be eventually
    imported from the grid if the required energy storage is not met.

    This value can also be used to determine how much excess energy is within storage at any
    given timestep.

    Args:
        elements: Mapping of element names to loaded configurations
        periods_hours: Duration of each optimization period in hours
        max_horizon_hours: Maximum lookahead duration in hours for blackout protection.
            If None, looks ahead to end of optimization horizon.

    Returns:
        RequiredEnergyResult containing:
        - required_energy: List of required energy values (kWh) at each timestep boundary (n_periods + 1).
          Each value represents the maximum battery drawdown from that point forward
          (limited by max_horizon_hours) before solar recharges the battery.
        - net_power: List of net power values (kW) for each period (n_periods).
          Positive = solar surplus, Negative = deficit (load > solar).

    """
    n_periods = len(periods_hours)
    periods_hours_array = np.array(periods_hours)

    # Add up all forecasted load
    total_load = np.zeros(n_periods)
    for config in elements.values():
        if config["element_type"] == ELEMENT_TYPE_LOAD:
            forecast = config["forecast"]
            total_load += np.array(forecast)

    # Add up all forecasted solar
    total_solar = np.zeros(n_periods)
    for config in elements.values():
        if config["element_type"] == ELEMENT_TYPE_SOLAR:
            forecast = config["forecast"]
            total_solar += np.array(forecast)

    # Calculate NET power (positive = surplus, negative = deficit)
    net_power = total_solar - total_load
    net_energy = net_power * periods_hours_array  # kWh per interval

    # For each timestep, find the maximum drawdown from that point forward
    # This is the deepest point the battery would drain to before solar recharges it
    required_energy: list[float] = []
    for t in range(n_periods + 1):
        if t >= n_periods:
            # At end of horizon, no future requirement
            required_energy.append(0.0)
        else:
            # Determine how many periods to look ahead based on max_horizon_hours
            if max_horizon_hours is not None:
                cumulative_hours = 0.0
                lookahead_periods = 0
                for i in range(t, n_periods):
                    cumulative_hours += periods_hours_array[i]
                    lookahead_periods += 1
                    if cumulative_hours >= max_horizon_hours:
                        break
                future_net = net_energy[t : t + lookahead_periods]
            else:
                future_net = net_energy[t:]

            if len(future_net) == 0:
                required_energy.append(0.0)
            else:
                # Calculate running balance from t forward
                running_balance = np.cumsum(future_net)
                # Maximum drawdown is the most negative point in the running balance
                max_drawdown = min(0.0, float(np.min(running_balance)))
                required_energy.append(abs(max_drawdown))

    return RequiredEnergyResult(
        required_energy=required_energy,
        net_power=net_power.tolist(),
    )
