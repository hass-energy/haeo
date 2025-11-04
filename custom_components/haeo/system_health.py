"""System health diagnostics for HAEO integration."""

from collections.abc import Mapping
from typing import Any

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import slugify

from .const import CONF_HORIZON_HOURS, CONF_PERIOD_MINUTES, DOMAIN, OPTIMIZATION_STATUS_PENDING
from .model import OUTPUT_NAME_OPTIMIZATION_COST, OUTPUT_NAME_OPTIMIZATION_DURATION, OUTPUT_NAME_OPTIMIZATION_STATUS


@callback
def async_register(
    hass: HomeAssistant,  # noqa: ARG001
    register: system_health.SystemHealthRegistration,
) -> None:
    """Register system health callbacks."""
    register.async_register_info(async_system_health_info)


async def async_system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Get system health information for HAEO integration."""
    health_info: dict[str, Any] = {}

    # Get all HAEO config entries
    entries = hass.config_entries.async_entries(DOMAIN)

    if not entries:
        health_info["status"] = "no_config_entries"
        return health_info

    # Check each config entry
    for entry in entries:
        entry_name = entry.title or entry.entry_id
        prefix = f"{entry_name}_"
        hub_key = slugify(str(entry_name))

        # Get coordinator from runtime data
        coordinator = entry.runtime_data

        if coordinator is None:
            health_info[f"{prefix}status"] = "coordinator_not_initialized"
            continue

        # Coordinator status
        health_info[f"{prefix}status"] = "ok" if coordinator.last_update_success else "update_failed"

        hub_outputs: Mapping[str, Any] = coordinator.data.get(hub_key, {}) if coordinator.data else {}

        status_output = hub_outputs.get(OUTPUT_NAME_OPTIMIZATION_STATUS)
        optimization_status = (
            status_output.state if status_output and status_output.state else OPTIMIZATION_STATUS_PENDING
        )
        health_info[f"{prefix}optimization_status"] = optimization_status

        cost_output = hub_outputs.get(OUTPUT_NAME_OPTIMIZATION_COST)
        duration_output = hub_outputs.get(OUTPUT_NAME_OPTIMIZATION_DURATION)

        if cost_output and cost_output.state is not None:
            health_info[f"{prefix}last_optimization_cost"] = f"{float(cost_output.state):.2f}"
        if duration_output and duration_output.state is not None:
            health_info[f"{prefix}last_optimization_duration"] = round(float(duration_output.state), 3)

        last_update_time = getattr(coordinator, "last_update_success_time", None)
        if last_update_time is not None:
            health_info[f"{prefix}last_optimization_time"] = last_update_time.isoformat()

        outputs_count = 0
        if coordinator.data:
            outputs_count = sum(
                len(outputs) for element_key, outputs in coordinator.data.items() if element_key != hub_key
            )
        health_info[f"{prefix}outputs"] = outputs_count

        horizon_hours = entry.data.get(CONF_HORIZON_HOURS)
        if horizon_hours is not None:
            health_info[f"{prefix}horizon_hours"] = horizon_hours

        period_minutes = entry.data.get(CONF_PERIOD_MINUTES)
        if period_minutes is not None:
            health_info[f"{prefix}period_minutes"] = period_minutes

    return health_info
