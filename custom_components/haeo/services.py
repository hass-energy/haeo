"""Service actions for HAEO integration."""

from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.json import ExtendedJSONEncoder
from homeassistant.helpers.system_info import async_get_system_info
from homeassistant.loader import Manifest, async_get_custom_components, async_get_integration
from homeassistant.setup import async_get_domain_setup_times
from homeassistant.util import dt as dt_util
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_SAVE_DIAGNOSTICS = "save_diagnostics"
SERVICE_OPTIMIZE = "optimize"
ATTR_CONFIG_ENTRY = "config_entry"
ATTR_TIMESTAMP = "time"


def _format_manifest(manifest: Manifest) -> Manifest:
    """Format manifest for diagnostics.

    Remove the @ from codeowners so that when users paste the codeowners
    into the repository, it will not notify the users in the codeowners file.
    """
    manifest_copy = manifest.copy()
    if "codeowners" in manifest_copy:
        manifest_copy["codeowners"] = [codeowner.lstrip("@") for codeowner in manifest_copy["codeowners"]]
    return manifest_copy


async def _build_diagnostics_payload(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Build full diagnostics payload matching Home Assistant's format.

    Includes system info, custom components, integration manifest, and setup times.
    """
    # Get system info
    hass_sys_info = await async_get_system_info(hass)
    hass_sys_info["run_as_root"] = hass_sys_info["user"] == "root"
    del hass_sys_info["user"]

    # Get custom components info
    all_custom_components = await async_get_custom_components(hass)
    custom_components = {
        cc_domain: {
            "documentation": cc_obj.documentation,
            "version": cc_obj.version,
            "requirements": cc_obj.requirements,
        }
        for cc_domain, cc_obj in all_custom_components.items()
    }

    # Get integration manifest
    integration = await async_get_integration(hass, DOMAIN)

    # Get issues for this domain
    issue_registry = ir.async_get(hass)
    issues = [issue_reg.to_json() for issue_id, issue_reg in issue_registry.issues.items() if issue_id[0] == DOMAIN]

    return {
        "home_assistant": hass_sys_info,
        "custom_components": custom_components,
        "integration_manifest": _format_manifest(integration.manifest),
        "setup_times": async_get_domain_setup_times(hass, DOMAIN),
        "data": data,
        "issues": issues,
    }


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up HAEO services."""

    async def async_handle_save_diagnostics(call: ServiceCall) -> None:
        """Handle the save_diagnostics service call."""
        # Import diagnostics module here to avoid circular imports
        from .diagnostics import collect_diagnostics  # noqa: PLC0415

        entry_id = call.data[ATTR_CONFIG_ENTRY]
        target_timestamp: datetime | None = call.data.get(ATTR_TIMESTAMP)

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

        # Get diagnostics data — pass as_of for historical, omit for current
        result = await collect_diagnostics(hass, entry, as_of=target_timestamp)

        # Validate that historical queries returned all expected data
        if target_timestamp is not None and result.missing_entity_ids:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="no_history_at_time",
                translation_placeholders={
                    "time": target_timestamp.isoformat(),
                    "missing": ", ".join(result.missing_entity_ids),
                },
            )

        # Generate filename with timestamp (microseconds for uniqueness)
        file_timestamp = (target_timestamp or dt_util.now()).strftime("%Y-%m-%d_%H%M%S.%f")
        filename = f"diagnostics_{file_timestamp}.json"
        filepath = Path(hass.config.path("haeo", "diagnostics", filename))

        # Build full diagnostics payload matching Home Assistant's format
        output = await _build_diagnostics_payload(hass, result.data)

        # Write to file (in executor to avoid blocking)
        def write_diagnostics() -> None:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with filepath.open("w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, cls=ExtendedJSONEncoder)

        await hass.async_add_executor_job(write_diagnostics)

        _LOGGER.info("HAEO diagnostics saved to %s", filepath)

    # Build schema - only include timestamp if recorder is available
    schema_fields: dict[vol.Marker, Any] = {vol.Required(ATTR_CONFIG_ENTRY): cv.string}
    if "recorder" in hass.config.components:
        schema_fields[vol.Optional(ATTR_TIMESTAMP)] = cv.datetime

    hass.services.async_register(
        DOMAIN,
        SERVICE_SAVE_DIAGNOSTICS,
        async_handle_save_diagnostics,
        schema=vol.Schema(schema_fields),
    )

    async def async_handle_run_optimizer(call: ServiceCall) -> None:
        """Handle the run_optimizer service call.

        Manually triggers optimization, bypassing debouncing and the auto-optimize setting.
        """
        # Import here to avoid circular imports
        from . import HaeoConfigEntry  # noqa: PLC0415

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

        # Get runtime data and coordinator
        typed_entry: HaeoConfigEntry = entry  # type: ignore[assignment]
        runtime_data = typed_entry.runtime_data
        if not runtime_data or not runtime_data.coordinator:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="config_entry_not_loaded",
                translation_placeholders={"entry_id": entry_id, "state": "no coordinator"},
            )

        # Run optimization
        _LOGGER.info("Running optimization for %s (manual trigger)", entry_id)
        await runtime_data.coordinator.async_run_optimization()

    hass.services.async_register(
        DOMAIN,
        SERVICE_OPTIMIZE,
        async_handle_run_optimizer,
        schema=vol.Schema({vol.Required(ATTR_CONFIG_ENTRY): cv.string}),
    )
