"""High-level data loading entrypoint.

This module exposes `load_network()` which converts a saved configuration
(`ConfigEntry.data`) into a fully populated `Network` instance ready for
optimization.  All field handling is delegated to specialised Loader
implementations found in sibling modules.
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
    ElementConfigData,
    ElementConfigSchema,
    battery,
    grid,
    load,
    photovoltaics,
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
    """Return a fully-populated `Network`.

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
    # Sort so connections are added last - they need their source/target elements to exist
    forecast_times_list = list(forecast_times)
    sorted_participants = sorted(
        participants.values(),
        key=lambda c: c[CONF_ELEMENT_TYPE] == ELEMENT_TYPE_CONNECTION,
    )
    for element_config in sorted_participants:
        # Load all fields using the high-level config_load function
        loaded_params: ElementConfigData = await config_load(
            element_config,
            hass=hass,
            forecast_times=forecast_times_list,
        )

        # Use adapter layer to convert config to model elements
        # The adapter returns a list of element configs (e.g., SourceSink + Connection)
        element_type = loaded_params[CONF_ELEMENT_TYPE]

        # Try to use element adapter if available
        adapter_module = None
        if element_type == "battery":
            adapter_module = battery
        elif element_type == "grid":
            adapter_module = grid
        elif element_type == "load":
            adapter_module = load
        elif element_type == "photovoltaics":
            adapter_module = photovoltaics

        if adapter_module and hasattr(adapter_module, "create_model_elements"):
            # Use adapter to create model elements
            model_elements = adapter_module.create_model_elements(
                loaded_params, period_hours, n_periods
            )
            for model_element_config in model_elements:
                net.add(**model_element_config)
        else:
            # Fallback for elements without adapters (like node, connection)
            loaded_kwargs: dict[str, Any] = dict(loaded_params)
            net.add(**loaded_kwargs)

    return net
