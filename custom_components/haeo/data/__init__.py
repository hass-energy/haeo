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
from homeassistant.helpers.update_coordinator import UpdateFailed

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


async def load_network(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    period_seconds: int,
    n_periods: int,
    participants: Mapping[str, ElementConfigSchema],
    forecast_times: Sequence[int],
) -> Network:
    """Return a fully-populated `Network` ready for optimization.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        period_seconds: Optimization period in seconds
        n_periods: Number of periods
        participants: Mapping of validated element names to configurations
        forecast_times: Rounded timestamps for each optimization period (epoch seconds)

    Raises:
        ValueError: when required sensor/forecast data is missing.

    """
    if not participants:
        _LOGGER.warning("No participants configured for hub")
        msg = "No participants configured"
        raise ValueError(msg)

    # Check that all required sensor data is available before loading
    missing_sensors: list[str] = []
    for name, element_config in participants.items():
        # Check availability for entire config
        if not config_available(
            element_config,
            hass=hass,
            forecast_times=forecast_times,
        ):
            missing_sensors.append(name)

    if missing_sensors:
        raise UpdateFailed(
            translation_key="missing_sensors",
            translation_placeholders={"unavailable_sensors": ", ".join(missing_sensors)},
        )

    # ==================================================================================
    # Unit boundary: seconds → hours
    # ==================================================================================
    # The coordinator and data loading layers work in seconds (practical for timestamps).
    # The model/optimization layer works in hours (necessary for kW·h = kWh math).
    # This is where we convert period from seconds to hours for the model layer.
    # ==================================================================================
    period_hours = period_seconds / 3600

    # Build network with period in hours
    net = Network(name=f"haeo_network_{entry.entry_id}", period=period_hours, n_periods=n_periods)

    # Get the data for each participant and add to the network
    # This converts from Schema mode (with entity IDs) to Data mode (with loaded values)
    forecast_times_list = list(forecast_times)

    # Collect all model elements from all config elements first
    all_model_elements: list[dict[str, Any]] = []
    for element_config in participants.values():
        # Load all fields using the high-level config_load function
        loaded_params: ElementConfigData = await config_load(
            element_config,
            hass=hass,
            forecast_times=forecast_times_list,
        )

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
