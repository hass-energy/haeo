"""Calculate required energy using maximum drawdown algorithm."""

from collections.abc import Mapping, Sequence

import numpy as np

from custom_components.haeo.elements import ELEMENT_TYPE_LOAD, ELEMENT_TYPE_SOLAR, ElementConfigData


def calculate_required_energy(
    elements: Mapping[str, ElementConfigData],
    periods_hours: Sequence[float],
) -> list[float]:
    """Calculate the required energy at each timestep using maximum drawdown.

    The required energy represents the minimum energy needed (e.g. battery storage) at each
    timestep to remain self-sufficient for the rest of the optimization horizon.

    Given a typical grid-connected solar + battery system, energy will have to be eventually
    imported from the grid if the required energy storage is not met.

    This value can also be used to determine how much excess energy is within storage at any
    given timestep.

    Returns:
        List of required energy values (kWh) at each timestep boundary (n_periods + 1).
        Each value represents the maximum battery drawdown from that point forward
        before solar recharges the battery.

    """
    n_periods = len(periods_hours)

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
