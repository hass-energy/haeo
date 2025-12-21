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
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.const import (
    CONF_BLACKOUT_DURATION_HOURS,
    CONF_BLACKOUT_PROTECTION,
    CONF_ELEMENT_TYPE,
    DEFAULT_BLACKOUT_DURATION_HOURS,
    DEFAULT_BLACKOUT_PROTECTION,
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    NETWORK_DEVICE_NETWORK,
)
from custom_components.haeo.elements import (
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPES,
    ElementConfigData,
    ElementConfigSchema,
)
from custom_components.haeo.model import Network
from custom_components.haeo.schema import available as config_available
from custom_components.haeo.schema import load as config_load

from .util.required_energy import calculate_required_energy

_LOGGER = logging.getLogger(__name__)

# Entity key for the blackout slack penalty number (must match number.py)
_BLACKOUT_SLACK_PENALTY_KEY = "blackout_slack_penalty"


def _get_blackout_slack_penalty(hass: HomeAssistant, entry: ConfigEntry) -> float:
    """Get the blackout slack penalty value from the number entity.

    Args:
        hass: Home Assistant instance
        entry: Config entry

    Returns:
        The blackout slack penalty value, or 0.2 if entity not found or unavailable.

    """
    # Find the Network subentry to construct the entity unique_id
    network_subentry = None
    for subentry in entry.subentries.values():
        if subentry.subentry_type == ELEMENT_TYPE_NETWORK:
            network_subentry = subentry
            break

    if network_subentry is None:
        _LOGGER.debug("No Network subentry found, using default blackout slack penalty")
        return 0.2

    # Construct the unique_id for the number entity (must match number.py)
    unique_id = (
        f"{entry.entry_id}_{network_subentry.subentry_id}_{NETWORK_DEVICE_NETWORK}_{_BLACKOUT_SLACK_PENALTY_KEY}"
    )

    # Look up the entity by unique_id
    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get_entity_id("number", DOMAIN, unique_id)

    if entity_entry is None:
        _LOGGER.debug("Blackout slack penalty entity not found, using default")
        return 0.2

    # Get the current state
    state = hass.states.get(entity_entry)
    if state is None or state.state in ("unknown", "unavailable"):
        _LOGGER.debug("Blackout slack penalty entity unavailable, using default")
        return 0.2

    try:
        value = float(state.state)
        _LOGGER.debug("Using blackout slack penalty: %s", value)
        return value
    except (ValueError, TypeError):
        _LOGGER.warning("Invalid blackout slack penalty value %s, using default", state.state)
        return 0.2


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
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    periods_seconds: Sequence[int],
    participants: Mapping[str, ElementConfigData],
) -> Network:
    """Return a fully-populated `Network` ready for optimization.

    Args:
        hass: Home Assistant instance
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

    # Read blackout slack penalty from number entity if blackout protection is enabled
    blackout_slack_penalty = 0.2  # Default value
    if blackout_protection:
        blackout_slack_penalty = _get_blackout_slack_penalty(hass, entry)

    # Calculate required energy with optional horizon limit for blackout protection
    # A duration of 0 means unlimited (look at entire remaining horizon)
    max_horizon_hours = blackout_duration_hours if blackout_protection and blackout_duration_hours > 0 else None
    energy_result = calculate_required_energy(participants, periods_hours, max_horizon_hours)

    net = Network(
        name=f"haeo_network_{entry.entry_id}",
        periods=periods_hours,
        required_energy=energy_result.required_energy,
        blackout_protection=blackout_protection,
        blackout_slack_penalty=blackout_slack_penalty,
        net_power=energy_result.net_power,
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
