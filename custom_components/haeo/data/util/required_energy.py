"""Calculate required energy using maximum drawdown algorithm.

The required energy represents the maximum battery capacity needed at each
timestep to survive until solar (or other uncontrollable generation) recharges
the battery.
"""

from collections.abc import Mapping, Sequence

import numpy as np

from custom_components.haeo.elements import ElementConfigData


def calculate_required_energy(
    participants: Mapping[str, ElementConfigData],
    periods_hours: Sequence[float],
) -> list[float]:
    """Calculate the required energy at each timestep using maximum drawdown.

    This is calculated BEFORE optimization so model elements can use it.

    The required energy represents the maximum battery capacity needed at each
    timestep to survive until solar (or other uncontrollable generation) recharges
    the battery. This uses a "maximum drawdown" approach that accounts for solar
    surplus periods that can recharge the battery.

    Returns:
        List of required energy values (kWh) at each timestep boundary (n_periods + 1).
        Each value represents the maximum battery drawdown from that point forward
        before solar recharges the battery.

    """
    n_periods = len(periods_hours)

    if n_periods == 0:
        return [0.0]

    # Aggregate all load forecasts
    total_load = np.zeros(n_periods)
    for config in participants.values():
        if config.get("element_type") == "load":
            forecast = config.get("forecast")
            if forecast is not None:
                total_load += np.array(forecast)

    # Aggregate all uncontrollable generation (solar, future: wind, etc.)
    total_uncontrollable = np.zeros(n_periods)
    for config in participants.values():
        if config.get("element_type") == "solar":
            forecast = config.get("forecast")
            if forecast is not None:
                total_uncontrollable += np.array(forecast)

    # Calculate NET power (positive = surplus, negative = deficit)
    net_power = total_uncontrollable - total_load
    net_energy = net_power * np.array(periods_hours)  # kWh per interval

    # For each timestep, find the maximum drawdown from that point forward
    # This is the deepest point the battery would drain to before solar recharges it
    required_energy: list[float] = []
    for t in range(n_periods + 1):
        if t >= n_periods:
            # At end of horizon, no future requirement
            required_energy.append(0.0)
        else:
            # Calculate running balance from t forward
            future_net = net_energy[t:]
            running_balance = np.cumsum(future_net)
            # Maximum drawdown is the most negative point in the running balance
            max_drawdown = min(0.0, float(np.min(running_balance)))
            required_energy.append(abs(max_drawdown))

    return required_energy
