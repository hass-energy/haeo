"""High-level data loading entrypoint.

This module exposes `load_network()` which converts a saved configuration
(`ConfigEntry.data`) into a fully populated `Network` instance ready for
optimization.  All field handling is delegated to specialised Loader
implementations found in sibling modules.
"""

from collections.abc import Mapping
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.haeo.elements import ElementConfigData, ElementConfigSchema
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
) -> Network | None:
    """Return a fully-populated `Network`.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        period_seconds: Optimization period in seconds
        n_periods: Number of periods
        participants: Mapping of validated element names to configurations

    Raises:
        ValueError: when required sensor/forecast data is missing.

    """
    if not participants:
        _LOGGER.warning("No participants configured for hub")
        return None

    # Check that all required sensor data is available before loading
    missing_sensors: list[str] = []
    for name, element_config in participants.items():
        # Check availability for entire config
        if not config_available(
            element_config,
            hass=hass,
            forecast_times=[],  # Empty for availability check
        ):
            missing_sensors.append(name)

    if missing_sensors:
        raise ValueError("Missing sensor data for: " + ", ".join(missing_sensors))

    # Round the time to the nearest period
    # Round down to the nearest multiple of period_seconds
    epoch_seconds = dt_util.utcnow().timestamp()
    rounded_epoch = (epoch_seconds // period_seconds) * period_seconds
    dt_util.utc_from_timestamp(rounded_epoch)
    origin_time = dt_util.utc_from_timestamp(rounded_epoch)

    # Calculate forecast times for the optimization period
    forecast_times = []
    for i in range(n_periods):
        period_time = origin_time + timedelta(seconds=period_seconds * i)
        forecast_times.append(int(period_time.timestamp()))

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
    for element_config in participants.values():
        # Load all fields using the high-level config_load function
        loaded_params: ElementConfigData = await config_load(
            element_config,
            hass=hass,
            forecast_times=forecast_times,
        )

        # net.add expects ElementConfigData with loaded values
        loaded_kwargs: dict[str, Any] = dict(loaded_params)
        net.add(**loaded_kwargs)

    return net
