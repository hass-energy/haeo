"""High-level data loading entrypoint.

This module exposes `load_network()` which converts a saved configuration
(`ConfigEntry.data`) into a fully populated `Network` instance ready for
optimization.  All field handling is delegated to specialised Loader
implementations found in sibling modules.
"""

from dataclasses import MISSING, fields
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.data import loader
from custom_components.haeo.data.loader import forecast_and_sensor_loader
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
        participant_configs[name] = data_to_config(config_cls, p_data)

    # Check that all required data is available and get the most recent update time to use as base time
    missing: list[str] = []
    for name, config in participant_configs.items():
        for f in fields(config):
            if f.name not in ("element_type", "name") and not loader.available(hass, f.name, type(config)):
                missing.append(f"{name}.{f.name} ({get_property_type(f.name, type(config))})")

    if missing:
        raise ValueError("Missing data for: " + ", ".join(missing))

    # TODO get the most recent update time to use as the base time from the sensors in use
    # TODO round the time to the nearest period

    # Build network
    net = Network(name=f"haeo_network_{entry.entry_id}", period=period_seconds, n_periods=n_periods)

    # Get the data for each participant and add to the network
    for name, config in participant_configs.items():
        params: dict[str, Any] = {}
        for f in fields(config):
            params[f.name] = await loader.load(hass, f.name, type(config), forecast_times=forecast_times)
        net.add(config.element_type, name, **params)

    return net
