"""High-level data loading entrypoint.

This module exposes `load_network()` which converts a saved configuration
(`ConfigEntry.data`) into a fully populated `Network` instance ready for
optimization.  All field handling is delegated to specialised Loader
implementations found in sibling modules.
"""

from dataclasses import fields
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.data import loader
from custom_components.haeo.model import Network
from custom_components.haeo.schema import data_to_config
from custom_components.haeo.types import ELEMENT_TYPES, ElementConfig

_LOGGER = logging.getLogger(__name__)


async def load_network(
    hass: HomeAssistant, entry: ConfigEntry, *, period_seconds: int, n_periods: int
) -> Network | None:
    """Return a fully-populated `Network`.

    Raises:
        ValueError: when required sensor/forecast data is missing.

    """
    # These are the times which will be used to load the data
    cfg = entry.data
    participants: dict[str, dict[str, Any]] = cfg.get("participants", {})
    if not participants:
        _LOGGER.warning("No participants configured for hub")
        return None

    # Convert raw participant dicts -> typed config objects (dataclasses)
    participant_configs: dict[str, ElementConfig] = {}
    for name, p_data in participants.items():
        element_type = p_data[CONF_ELEMENT_TYPE]
        config_cls = ELEMENT_TYPES.get(element_type)
        if not config_cls:
            _LOGGER.error("Unknown element type %s", element_type)
            continue
        participant_configs[name] = data_to_config(
            config_cls, p_data, participants=participants, current_element_name=name
        )

    # Check that all required sensor data is available before loading
    missing_sensors: list[str] = []
    for name, config in participant_configs.items():
        for f in fields(config):
            if f.name not in ("element_type", "name"):
                field_value = getattr(config, f.name)

                # Check if sensor/forecast data is available
                if not loader.available(
                    hass=hass,
                    field_name=f.name,
                    config_class=type(config),
                    value=field_value,
                    forecast_times=[],  # Empty for availability check
                ):
                    missing_sensors.append(f"{name}.{f.name}")

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

    # Build network
    net = Network(name=f"haeo_network_{entry.entry_id}", period=period_seconds, n_periods=n_periods)

    # Get the data for each participant and add to the network
    for config in participant_configs.values():
        params: dict[str, Any] = {}
        for f in fields(config):
            field_value = getattr(config, f.name)
            params[f.name] = await loader.load(hass, f.name, type(config), forecast_times=forecast_times)
        net.add(**params)

    return net
