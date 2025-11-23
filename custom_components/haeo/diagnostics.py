"""Diagnostics support for HAEO integration."""

import json
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import __version__ as ha_version
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .const import CONF_ELEMENT_TYPE, CONF_HORIZON_HOURS, CONF_PERIOD_MINUTES
from .coordinator import HaeoDataUpdateCoordinator, extract_entity_ids_from_config
from .elements import is_element_config_schema


async def async_get_config_entry_diagnostics(hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a HAEO config entry.

    Returns a dict with four main keys:
    - config: HAEO configuration (participants, horizon, period)
    - inputs: Input sensor states used in optimization
    - outputs: Output sensor states from optimization results
    - environment: Environment information (HA version, HAEO version, timestamp)
    """
    coordinator: HaeoDataUpdateCoordinator | None = config_entry.runtime_data

    # Build config section with participants
    config: dict[str, Any] = {
        "participants": {},
        CONF_HORIZON_HOURS: config_entry.data.get(CONF_HORIZON_HOURS),
        CONF_PERIOD_MINUTES: config_entry.data.get(CONF_PERIOD_MINUTES),
    }

    # Transform subentries into participants dict
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "network":
            raw_data = dict(subentry.data)
            raw_data.setdefault("name", subentry.title)
            raw_data.setdefault(CONF_ELEMENT_TYPE, subentry.subentry_type)
            config["participants"][subentry.title] = raw_data

    # Collect input sensor states for all entities used in the configuration
    all_entity_ids: set[str] = set()
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "network":
            # Create config dict with element_type
            participant_config = dict(subentry.data)
            participant_config[CONF_ELEMENT_TYPE] = subentry.subentry_type
            # Try to extract entity IDs - use type guard for safety
            if is_element_config_schema(participant_config):
                all_entity_ids.update(extract_entity_ids_from_config(participant_config))
            # Even if validation fails, try to extract entity IDs anyway for diagnostics
            # This helps with incomplete or invalid configs
            else:
                try:
                    from .coordinator import collect_entity_ids  # noqa: PLC0415

                    for value in participant_config.values():
                        all_entity_ids.update(collect_entity_ids(value))
                except Exception:  # noqa: S110
                    pass  # Skip on error

    # Extract input states using State.as_dict() - use list comprehension
    inputs: list[dict[str, Any]] = [
        state.as_dict() for entity_id in sorted(all_entity_ids) if (state := hass.states.get(entity_id)) is not None
    ]

    # Collect output sensor states if coordinator has data
    outputs: list[dict[str, Any]] = []
    if coordinator and coordinator.data:
        subentry_by_slug: dict[str, ConfigSubentry] = {
            slugify(subentry.title): subentry for subentry in config_entry.subentries.values()
        }

        for element_key, element_outputs in coordinator.data.items():
            output_subentry: ConfigSubentry | None = subentry_by_slug.get(element_key)
            if output_subentry is not None:
                for output_name in element_outputs:
                    unique_id = f"{config_entry.entry_id}_{output_subentry.subentry_id}_{output_name}"
                    entity_id = f"sensor.{config_entry.domain}_{unique_id}"
                    state = hass.states.get(entity_id)
                    if state is not None:
                        outputs.append(state.as_dict())

    # Get HAEO version from manifest.json
    manifest_path = Path(__file__).parent / "manifest.json"
    try:
        with manifest_path.open() as f:
            manifest = json.load(f)
        haeo_version = manifest.get("version", "unknown")
    except (FileNotFoundError, json.JSONDecodeError):
        haeo_version = "unknown"

    # Build environment section
    now = dt_util.now()
    environment: dict[str, Any] = {
        "ha_version": ha_version,
        "haeo_version": haeo_version,
        "timestamp": now.isoformat(),
        "timezone": str(dt_util.get_default_time_zone()),
    }

    # Return dict with alphabetically sorted keys
    # This puts config and environment first, then inputs and outputs
    return {
        "config": config,
        "environment": environment,
        "inputs": inputs,
        "outputs": outputs,
    }
