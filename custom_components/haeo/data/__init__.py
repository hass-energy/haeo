"""High-level data loading entrypoint.

This module exposes `load_network()` which converts a saved configuration
(`ConfigEntry.data`) into a fully populated `Network` instance ready for
optimization.  All field handling is delegated to specialised Loader
implementations found in sibling modules.

The adapter layer transforms configuration elements into model elements:
    Configuration Element (with entity IDs) →
    Adapter.create_model_elements() →
    Model Elements (pure optimization)
"""

from collections.abc import Mapping, Sequence
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.elements import (
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPES,
    ElementConfigData,
    ElementConfigSchema,
)
from custom_components.haeo.model import Network
from custom_components.haeo.schema import available as config_available
from custom_components.haeo.schema import load as config_load

_LOGGER = logging.getLogger(__name__)


async def load_element_configs(
    hass: HomeAssistant,
    participants: Mapping[str, ElementConfigSchema],
    forecast_times: Sequence[float],
) -> dict[str, ElementConfigData]:
    """Load sensor values for all element configurations.

    Converts ElementConfigSchema (with entity IDs) to ElementConfigData (with loaded values).

    Args:
        hass: Home Assistant instance
        participants: Mapping of element names to configurations with entity IDs
        forecast_times: Rounded timestamps for each optimization period (epoch seconds)

    Returns:
        Mapping of element names to loaded configurations with values

    Raises:
        ValueError: when required sensor/forecast data is missing

    """
    loaded_configs: dict[str, ElementConfigData] = {}
    forecast_times_list = list(forecast_times)

    for element_name, element_config in participants.items():
        # Load all fields using the high-level config_load function
        loaded_params: ElementConfigData = await config_load(
            element_config,
            hass=hass,
            forecast_times=forecast_times_list,
        )
        loaded_configs[element_name] = loaded_params

    return loaded_configs


def calculate_required_energy(
    participants: Mapping[str, ElementConfigData],
    periods_hours: Sequence[float],
) -> list[float]:
    """Calculate the required energy at each timestep.

    This is calculated BEFORE optimization so model elements can use it.

    The required energy represents the total future energy that must come from
    dispatchable sources (battery, grid, generator) to meet load that exceeds
    uncontrollable generation (solar, wind).

    Returns:
        List of required energy values (kWh) at each timestep boundary (n_periods + 1).
        Each value represents the total energy required from dispatchable sources
        from that point until the end of the horizon.

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

    # Calculate net power (positive = surplus, negative = requires dispatchable)
    net_power = total_uncontrollable - total_load

    # Extract only requirements (negative values become positive energy requirements)
    required_power = np.maximum(0.0, -net_power)  # kW
    required_interval = required_power * np.array(periods_hours)  # kWh

    # Reverse cumulative sum: how much required energy from t to end
    required_energy = np.cumsum(required_interval[::-1])[::-1]

    # Add terminal zero (at end of horizon, no future requirement)
    required_energy = np.concatenate([required_energy, [0.0]])

    return required_energy.tolist()


async def load_network(
    entry: ConfigEntry,
    *,
    periods_seconds: Sequence[int],
    participants: Mapping[str, ElementConfigData],
) -> Network:
    """Return a fully-populated `Network` ready for optimization.

    Args:
        entry: Config entry
        periods_seconds: Sequence of optimization period durations in seconds
        participants: Mapping of element names to loaded configurations (with values)

    Raises:
        ValueError: when required sensor/forecast data is missing.

    """
    if not participants:
        _LOGGER.warning("No participants configured for hub")
        msg = "No participants configured"
        raise ValueError(msg)

    # ==================================================================================
    # Unit boundary: seconds → hours
    # ==================================================================================
    # The coordinator and data loading layers work in seconds (practical for timestamps).
    # The model/optimization layer works in hours (necessary for kW·h = kWh math).
    # This is where we convert periods from seconds to hours for the model layer.
    # ==================================================================================
    periods_hours = [s / 3600 for s in periods_seconds]

    # Calculate required energy BEFORE building network (available to model elements)
    required_energy = calculate_required_energy(participants, periods_hours)

    # Build network with periods in hours and required_energy available
    net = Network(
        name=f"haeo_network_{entry.entry_id}",
        periods=periods_hours,
        required_energy=required_energy,
    )

    # Collect all model elements from all config elements
    all_model_elements: list[dict[str, Any]] = []
    for loaded_params in participants.values():
        # Use registry entry to create model elements from configuration element
        element_type = loaded_params[CONF_ELEMENT_TYPE]
        model_elements = ELEMENT_TYPES[element_type].create_model_elements(loaded_params)
        all_model_elements.extend(model_elements)

    # Sort all model elements so connections are added last
    # This ensures connection source/target elements exist when connections are registered
    sorted_model_elements = sorted(
        all_model_elements,
        key=lambda e: e.get("element_type") == ELEMENT_TYPE_CONNECTION,
    )

    # Add all model elements to network in correct order
    for model_element_config in sorted_model_elements:
        try:
            net.add(**model_element_config)
        except Exception as e:
            msg = (
                f"Failed to add model element '{model_element_config.get('name')}' "
                f"(type={model_element_config.get('element_type')})"
            )
            _LOGGER.exception(msg)
            raise ValueError(msg) from e

    return net


__all__ = [
    "calculate_required_energy",
    "config_available",
    "load_element_configs",
    "load_network",
]
