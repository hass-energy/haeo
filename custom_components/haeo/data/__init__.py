"""High-level data loading entrypoint.

This module exposes `load_network()` which converts a saved configuration
(`ConfigEntry.data`) into a fully populated `Network` instance ready for
optimization.  All field handling is delegated to specialised Loader
implementations found in sibling modules.
"""

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.model import Network
from custom_components.haeo.schema import available as config_available
from custom_components.haeo.schema import data_to_config
from custom_components.haeo.schema import load as config_load
from custom_components.haeo.types import ELEMENT_TYPES, ElementConfigSchema

_LOGGER = logging.getLogger(__name__)


async def load_network(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    period_seconds: int,
    n_periods: int,
    config: dict[str, Any] | None = None,
) -> Network | None:
    """Return a fully-populated `Network`.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        period_seconds: Optimization period in seconds
        n_periods: Number of periods
        config: Optional config dict (if not provided, uses entry.data)

    Raises:
        ValueError: when required sensor/forecast data is missing.

    """
    # These are the times which will be used to load the data
    cfg = config if config is not None else entry.data
    participants: dict[str, dict[str, Any]] = cfg.get("participants", {})
    if not participants:
        _LOGGER.warning("No participants configured for hub")
        return None

    # Convert raw participant dicts -> typed config objects (TypedDicts in Schema mode)
    participant_configs: dict[str, ElementConfigSchema] = {}
    for name, p_data in participants.items():
        element_type = p_data[CONF_ELEMENT_TYPE]
        element_types = ELEMENT_TYPES.get(element_type)
        if not element_types:
            _LOGGER.error("Unknown element type %s", element_type)
            continue
        schema_cls, _, _ = element_types
        participant_configs[name] = data_to_config(
            schema_cls, p_data, participants=participants, current_element_name=name
        )

    # Check that all required sensor data is available before loading
    missing_sensors: list[str] = []
    for name, element_config in participant_configs.items():
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
    for element_config in participant_configs.values():
        # Load all fields using the high-level config_load function
        loaded_params = await config_load(
            element_config,
            hass=hass,
            forecast_times=forecast_times,
        )

        # net.add expects ElementConfigData with loaded values
        net.add(**loaded_params)

    return net
