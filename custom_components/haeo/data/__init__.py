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

from custom_components.haeo.const import (
    CONF_BLACKOUT_DURATION_HOURS,
    CONF_BLACKOUT_PROTECTION,
    CONF_ELEMENT_TYPE,
    DEFAULT_BLACKOUT_DURATION_HOURS,
    DEFAULT_BLACKOUT_PROTECTION,
)
from custom_components.haeo.elements import ELEMENT_TYPE_BATTERY, ELEMENT_TYPES, ElementConfigData, ElementConfigSchema
from custom_components.haeo.model import Network
from custom_components.haeo.schema import available as config_available
from custom_components.haeo.schema import load as config_load

from .util.required_energy import calculate_required_energy

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

    # Read blackout protection settings from config entry
    blackout_protection = entry.data.get(CONF_BLACKOUT_PROTECTION, DEFAULT_BLACKOUT_PROTECTION)
    blackout_duration_hours = entry.data.get(CONF_BLACKOUT_DURATION_HOURS, DEFAULT_BLACKOUT_DURATION_HOURS)

    # Calculate required energy with optional horizon limit for blackout protection
    # A duration of 0 means unlimited (look at entire remaining horizon)
    max_horizon_hours = blackout_duration_hours if blackout_protection and blackout_duration_hours > 0 else None
    energy_result = calculate_required_energy(participants, periods_hours, max_horizon_hours)

    net = Network(
        name=f"haeo_network_{entry.entry_id}",
        periods=periods_hours,
        required_energy=energy_result.required_energy,
        blackout_protection=blackout_protection,
        net_power=energy_result.net_power,
    )

    # Collect all model elements from all config elements
    all_model_elements: list[dict[str, Any]] = []
    for element_params in participants.values():
        # Use registry entry to create model elements from configuration element
        element_type = element_params[CONF_ELEMENT_TYPE]

        # For battery elements, inject required_energy when blackout protection is enabled
        # This enables dynamic undercharge sizing based on energy needs
        params_to_use: ElementConfigData = element_params
        if element_type == ELEMENT_TYPE_BATTERY and blackout_protection:
            params_to_use = dict(element_params)  # type: ignore[assignment]
            params_to_use["required_energy"] = energy_result.required_energy  # type: ignore[typeddict-unknown-key]

        model_elements = ELEMENT_TYPES[element_type].create_model_elements(params_to_use)
        all_model_elements.extend(model_elements)

    # Sort all model elements so connections are added last
    # This ensures connection source/target elements exist when connections are registered
    # Both "connection" and "battery_balance_connection" need to be added after batteries
    sorted_model_elements = sorted(
        all_model_elements,
        key=lambda e: e.get("element_type", "").endswith("connection"),
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
