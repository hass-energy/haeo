"""Service actions for HAEO integration."""

from __future__ import annotations

from datetime import datetime
import json
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_SAVE_DIAGNOSTICS = "save_diagnostics"
ATTR_CONFIG_ENTRY = "config_entry"


def _json_default(obj: object) -> str:
    """Handle non-serializable objects like datetime."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    msg = f"Object of type {type(obj).__name__} is not JSON serializable"
    raise TypeError(msg)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up HAEO services."""

    async def async_handle_save_diagnostics(call: ServiceCall) -> None:
        """Handle the save_diagnostics service call."""
        # Import diagnostics module here to avoid circular imports
        from .diagnostics import async_get_config_entry_diagnostics  # noqa: PLC0415

        entry_id = call.data[ATTR_CONFIG_ENTRY]

        # Validate config entry exists
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="config_entry_not_found",
                translation_placeholders={"entry_id": entry_id},
            )

        # Validate it's a HAEO entry
        if entry.domain != DOMAIN:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="config_entry_wrong_domain",
                translation_placeholders={"entry_id": entry_id, "domain": entry.domain},
            )

        # Validate entry is loaded
        if entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="config_entry_not_loaded",
                translation_placeholders={"entry_id": entry_id, "state": str(entry.state)},
            )

        # Get diagnostics data
        diagnostics_data = await async_get_config_entry_diagnostics(hass, entry)

        # Generate filename with timestamp
        timestamp = dt_util.now().strftime("%Y%m%dT%H%M%S")
        filename = f"haeo_diagnostics_{entry_id}_{timestamp}.json"
        filepath = Path(hass.config.path(filename))

        # Wrap in {"data": ...} to match Home Assistant's diagnostics download format
        output = {"data": diagnostics_data}

        # Write to file (in executor to avoid blocking)
        def write_diagnostics() -> None:
            with filepath.open("w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False, default=_json_default)

        await hass.async_add_executor_job(write_diagnostics)

        _LOGGER.info("HAEO diagnostics saved to %s", filepath)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SAVE_DIAGNOSTICS,
        async_handle_save_diagnostics,
        schema=vol.Schema({vol.Required(ATTR_CONFIG_ENTRY): cv.string}),
    )
