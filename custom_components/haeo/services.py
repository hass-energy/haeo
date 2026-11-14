"""Service actions for HAEO integration."""

from collections.abc import Mapping, Sequence
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.json import ExtendedJSONEncoder
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.system_info import async_get_system_info
from homeassistant.loader import Manifest, async_get_custom_components, async_get_integration
from homeassistant.setup import async_get_domain_setup_times
from homeassistant.util import dt as dt_util
from homeassistant.util.json import JsonValueType
import voluptuous as vol

from .const import DOMAIN
from .core.adapters.offer import GridOffer, GridOfferStep

if TYPE_CHECKING:
    from . import HaeoRuntimeData
    from .coordinator import HaeoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_SAVE_DIAGNOSTICS = "save_diagnostics"
SERVICE_OPTIMIZE = "optimize"
SERVICE_OFFER_CURVE = "offer_curve"
ATTR_CONFIG_ENTRY = "config_entry"
ATTR_TIMESTAMP = "time"
ATTR_IMMEDIATE = "immediate"
ATTR_START = "start"
ATTR_END = "end"
ATTR_MIN_PRICE = "min_price"
ATTR_MAX_PRICE = "max_price"
ATTR_INTERVAL = "interval"
ATTR_EMISSIONS_INTENSITY = "emissions_intensity"
# The NEM's price floor and, roughly, its cap, in $/kWh
DEFAULT_MIN_PRICE: Final = -1.0
DEFAULT_MAX_PRICE: Final = 20.0
# Minutes in a settlement interval, the NEM's
DEFAULT_INTERVAL: Final = 5
# Decimal places offers are reported to: a hundredth of a cent, a watt, a gram per kWh and a gram
_PRICE_DIGITS: Final = 4
_POWER_DIGITS: Final = 3
_INTENSITY_DIGITS: Final = 3
_EMISSIONS_DIGITS: Final = 3


def _format_manifest(manifest: Manifest) -> Manifest:
    """Format manifest for diagnostics.

    Remove the @ from codeowners so that when users paste the codeowners
    into the repository, it will not notify the users in the codeowners file.
    """
    manifest_copy = manifest.copy()
    if "codeowners" in manifest_copy:
        manifest_copy["codeowners"] = [codeowner.lstrip("@") for codeowner in manifest_copy["codeowners"]]
    return manifest_copy


async def _build_diagnostics_payload(hass: HomeAssistant, data: dict[str, object]) -> dict[str, object]:
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


async def async_save_diagnostics(hass: HomeAssistant, data: dict[str, object], kind: str, time: datetime) -> Path:
    """Write a diagnostics file named for its kind and time, and return its path.

    Files go to ``haeo/diagnostics`` in the configuration directory, in the format
    Home Assistant's own diagnostics download uses.
    """
    # Microseconds keep files written in the same second apart
    filepath = Path(hass.config.path("haeo", "diagnostics", f"{kind}_{time:%Y-%m-%d_%H%M%S.%f}.json"))
    output = await _build_diagnostics_payload(hass, data)

    def write_diagnostics() -> None:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with filepath.open("w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, cls=ExtendedJSONEncoder)

    await hass.async_add_executor_job(write_diagnostics)
    _LOGGER.info("HAEO diagnostics saved to %s", filepath)
    return filepath


def _loaded_coordinator(hass: HomeAssistant, entry_id: str) -> "HaeoDataUpdateCoordinator":
    """Return the coordinator of a loaded HAEO config entry, raising when there is none."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="config_entry_not_found",
            translation_placeholders={"entry_id": entry_id},
        )

    if entry.domain != DOMAIN:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="config_entry_wrong_domain",
            translation_placeholders={"entry_id": entry_id, "domain": entry.domain},
        )

    if entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="config_entry_not_loaded",
            translation_placeholders={"entry_id": entry_id, "state": str(entry.state)},
        )

    # A loaded HAEO entry holds HAEO's runtime data
    runtime_data: HaeoRuntimeData | None = entry.runtime_data
    if not runtime_data or not runtime_data.coordinator:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="config_entry_not_loaded",
            translation_placeholders={"entry_id": entry_id, "state": "no coordinator"},
        )
    return runtime_data.coordinator


def _service_time(time: datetime) -> datetime:
    """Return a service call's time with a zone, reading a time without one in Home Assistant's.

    The datetime selector sends a time without a zone.
    """
    return time if time.tzinfo is not None else time.replace(tzinfo=dt_util.get_default_time_zone())


def _rounded(value: float, digits: int) -> float:
    """Return a value rounded to some decimal places, with a rounded negative zero as zero."""
    return round(value, digits) + 0.0


def _offer_step(step: GridOfferStep) -> dict[str, JsonValueType]:
    """Return an offer step as service response data, with its emissions when they were worked out."""
    data: dict[str, JsonValueType] = {
        "import_price": _rounded(step.import_price, _PRICE_DIGITS),
        "export_price": _rounded(step.export_price, _PRICE_DIGITS),
        "power": _rounded(step.power, _POWER_DIGITS),
    }
    if step.emissions is not None:
        data["emissions"] = _rounded(step.emissions, _EMISSIONS_DIGITS)
    return data


def _offer_response(timestamps: Sequence[float], offers: Mapping[str, Sequence[GridOffer]]) -> dict[str, JsonValueType]:
    """Return grid offers as service response data, each window named by its start and end time."""

    def time(timestamp: float) -> str:
        return dt_util.as_local(dt_util.utc_from_timestamp(timestamp)).isoformat()

    def window(offer: GridOffer) -> dict[str, JsonValueType]:
        data: dict[str, JsonValueType] = {
            "start": time(timestamps[offer.periods[0]]),
            "end": time(timestamps[offer.periods[-1] + 1]),
            "import_price": _rounded(offer.import_price, _PRICE_DIGITS),
            "export_price": _rounded(offer.export_price, _PRICE_DIGITS),
            "power": _rounded(offer.power, _POWER_DIGITS),
        }
        if offer.emissions_intensity is not None:
            data["emissions_intensity"] = _rounded(offer.emissions_intensity, _INTENSITY_DIGITS)
        data["offer"] = [_offer_step(step) for step in offer.steps]
        return data

    return {"grids": {grid: [window(offer) for offer in grid_offers] for grid, grid_offers in offers.items()}}


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up HAEO services."""

    async def async_handle_save_diagnostics(call: ServiceCall) -> None:
        """Handle the save_diagnostics service call."""
        # Import diagnostics module here to avoid circular imports
        from .diagnostics import collect_diagnostics  # noqa: PLC0415

        entry_id = call.data[ATTR_CONFIG_ENTRY]
        target_timestamp: datetime | None = call.data.get(ATTR_TIMESTAMP)
        # Left without a zone, the recorder would read the time in the OS zone
        if target_timestamp is not None:
            target_timestamp = _service_time(target_timestamp)

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

        # Past states come from the recorder
        if target_timestamp is not None and "recorder" not in hass.config.components:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="recorder_not_loaded")

        # Get diagnostics data — pass target_time for historical, omit for current
        result = await collect_diagnostics(hass, entry, target_time=target_timestamp)

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

        await async_save_diagnostics(hass, result.to_dict(), "diagnostics", target_timestamp or dt_util.now())

    # The file goes into the configuration directory and holds the whole HAEO configuration,
    # which only administrators can read through Home Assistant's own diagnostics download
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SAVE_DIAGNOSTICS,
        async_handle_save_diagnostics,
        schema=vol.Schema({vol.Required(ATTR_CONFIG_ENTRY): cv.string, vol.Optional(ATTR_TIMESTAMP): cv.datetime}),
    )

    async def async_handle_run_optimizer(call: ServiceCall) -> None:
        """Handle the run_optimizer service call.

        Returns once the next optimization has finished, whatever the auto-optimize
        setting. It starts at once unless the call turns immediate off, which waits
        out the debounce window.
        """
        entry_id = call.data[ATTR_CONFIG_ENTRY]
        coordinator = _loaded_coordinator(hass, entry_id)

        _LOGGER.info("Running optimization for %s (manual trigger)", entry_id)
        await coordinator.async_run_optimization(immediate=call.data[ATTR_IMMEDIATE])

    hass.services.async_register(
        DOMAIN,
        SERVICE_OPTIMIZE,
        async_handle_run_optimizer,
        schema=vol.Schema(
            {vol.Required(ATTR_CONFIG_ENTRY): cv.string, vol.Optional(ATTR_IMMEDIATE, default=True): cv.boolean}
        ),
    )

    async def async_handle_offer_curve(call: ServiceCall) -> ServiceResponse:
        """Return each grid's offer curve over the next settlement interval, or each one from a start to an end time."""
        coordinator = _loaded_coordinator(hass, call.data[ATTR_CONFIG_ENTRY])
        start: datetime | None = call.data.get(ATTR_START)
        end: datetime | None = call.data.get(ATTR_END)
        min_price: float = call.data[ATTR_MIN_PRICE]
        max_price: float = call.data[ATTR_MAX_PRICE]
        if min_price >= max_price:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="offer_price_range")
        timestamps, offers = await coordinator.async_grid_offers(
            start=_service_time(start if start is not None else dt_util.utcnow()).timestamp(),
            end=_service_time(end).timestamp() if end is not None else None,
            interval=call.data[ATTR_INTERVAL] * 60.0,
            emissions_intensity=call.data.get(ATTR_EMISSIONS_INTENSITY),
            min_price=min_price,
            max_price=max_price,
        )
        return _offer_response(timestamps, offers)

    hass.services.async_register(
        DOMAIN,
        SERVICE_OFFER_CURVE,
        async_handle_offer_curve,
        schema=vol.Schema(
            {
                vol.Required(ATTR_CONFIG_ENTRY): cv.string,
                vol.Optional(ATTR_START): cv.datetime,
                vol.Optional(ATTR_END): cv.datetime,
                vol.Optional(ATTR_MIN_PRICE, default=DEFAULT_MIN_PRICE): vol.Coerce(float),
                vol.Optional(ATTR_MAX_PRICE, default=DEFAULT_MAX_PRICE): vol.Coerce(float),
                vol.Optional(ATTR_INTERVAL, default=DEFAULT_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=1)),
                vol.Optional(ATTR_EMISSIONS_INTENSITY): cv.entity_id,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
