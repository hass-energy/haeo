"""System health diagnostics for HAEO integration."""

from homeassistant.components import system_health
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util
from homeassistant.util.json import JsonValueType

from . import HaeoConfigEntry
from .const import (
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    NETWORK_DEVICE_NETWORK,
    OPTIMIZATION_STATUS_PENDING,
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
)


@callback
def async_register(
    hass: HomeAssistant,  # noqa: ARG001 (required by HA system health registration callback signature)
    register: system_health.SystemHealthRegistration,
) -> None:
    """Register system health callbacks."""
    register.async_register_info(async_system_health_info)


async def async_system_health_info(hass: HomeAssistant) -> dict[str, JsonValueType]:
    """Get system health information for HAEO integration."""
    health_info: dict[str, JsonValueType] = {}

    entries: list[HaeoConfigEntry] = hass.config_entries.async_entries(DOMAIN)

    if not entries:
        health_info["status"] = "no_config_entries"
        return health_info

    for entry in entries:
        entry_name = entry.title or entry.entry_id
        prefix = f"{entry_name}_"

        # Runtime data only exists while the entry is loaded
        if entry.state is not ConfigEntryState.LOADED:
            health_info[f"{prefix}status"] = entry.state.value
            continue

        runtime_data = entry.runtime_data
        if runtime_data is None or runtime_data.coordinator is None:
            health_info[f"{prefix}status"] = "coordinator_not_initialized"
            continue

        coordinator = runtime_data.coordinator
        health_info[f"{prefix}status"] = "ok" if coordinator.last_update_success else "update_failed"

        # Network outputs live under the network subentry's title, on the network device
        network_subentry_title = next(
            s.title for s in entry.subentries.values() if s.subentry_type == ELEMENT_TYPE_NETWORK
        )
        outputs = coordinator.data.outputs if coordinator.data else {}
        network_outputs = outputs.get(network_subentry_title, {}).get(NETWORK_DEVICE_NETWORK, {})

        status_output = network_outputs.get(OUTPUT_NAME_OPTIMIZATION_STATUS)
        optimization_status = (
            status_output.state if status_output and status_output.state else OPTIMIZATION_STATUS_PENDING
        )
        health_info[f"{prefix}optimization_status"] = optimization_status

        cost_output = network_outputs.get(OUTPUT_NAME_OPTIMIZATION_COST)
        duration_output = network_outputs.get(OUTPUT_NAME_OPTIMIZATION_DURATION)

        if cost_output and cost_output.state is not None:
            health_info[f"{prefix}last_optimization_cost"] = f"{float(cost_output.state):.2f}"
        if duration_output and duration_output.state is not None:
            health_info[f"{prefix}last_optimization_duration"] = round(float(duration_output.state), 3)

        if coordinator.data:
            health_info[f"{prefix}last_optimization_time"] = dt_util.as_utc(coordinator.data.completed_at).isoformat()

        health_info[f"{prefix}outputs"] = sum(
            len(device_outputs)
            for subentry_title, devices in outputs.items()
            if subentry_title != network_subentry_title
            for device_outputs in devices.values()
        )

        # Report total number of periods and horizon in minutes
        periods_seconds = runtime_data.horizon_manager.periods_seconds
        total_periods = len(periods_seconds)
        if total_periods > 0:
            health_info[f"{prefix}total_periods"] = total_periods
            horizon_minutes = sum(periods_seconds) // 60
            health_info[f"{prefix}horizon_minutes"] = horizon_minutes

    return health_info
