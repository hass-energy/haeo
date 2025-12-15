"""System health diagnostics for HAEO integration."""

from collections.abc import Mapping
from typing import Any

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_TIER_1_COUNT,
    CONF_TIER_2_COUNT,
    CONF_TIER_3_COUNT,
    CONF_TIER_4_COUNT,
    DOMAIN,
    OPTIMIZATION_STATUS_PENDING,
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
    tiers_to_periods_seconds,
)


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
        hub_key = entry_name

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

        # Report total number of periods and horizon in minutes
        total_periods = (
            entry.data.get(CONF_TIER_1_COUNT, 0)
            + entry.data.get(CONF_TIER_2_COUNT, 0)
            + entry.data.get(CONF_TIER_3_COUNT, 0)
            + entry.data.get(CONF_TIER_4_COUNT, 0)
        )
        if total_periods > 0:
            health_info[f"{prefix}total_periods"] = total_periods
            # Calculate total horizon in minutes from periods
            periods_seconds = tiers_to_periods_seconds(entry.data)
            horizon_minutes = sum(periods_seconds) // 60
            health_info[f"{prefix}horizon_minutes"] = horizon_minutes

    return health_info
