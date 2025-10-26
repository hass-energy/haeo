"""System health diagnostics for HAEO integration."""

from typing import Any

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .const import CONF_HORIZON_HOURS, CONF_OPTIMIZER, CONF_PERIOD_MINUTES, DOMAIN


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

        # Get coordinator from runtime data
        coordinator = entry.runtime_data

        if coordinator is None:
            health_info[f"{prefix}status"] = "coordinator_not_initialized"
            continue

        # Coordinator status
        health_info[f"{prefix}status"] = "ok" if coordinator.last_update_success else "update_failed"

        # Optimization status reflected from coordinator metadata
        health_info[f"{prefix}optimization_status"] = getattr(coordinator, "optimization_status", "unknown")

        if coordinator.last_optimization_cost is not None:
            health_info[f"{prefix}last_optimization_cost"] = f"{coordinator.last_optimization_cost:.2f}"
        if coordinator.last_optimization_duration is not None:
            health_info[f"{prefix}last_optimization_duration"] = round(coordinator.last_optimization_duration, 3)
        if coordinator.last_optimization_time is not None:
            health_info[f"{prefix}last_optimization_time"] = coordinator.last_optimization_time.isoformat()

        outputs_count = sum(len(outputs) for outputs in coordinator.data.values()) if coordinator.data else 0
        health_info[f"{prefix}outputs"] = outputs_count

        optimizer = coordinator.config.get(CONF_OPTIMIZER)
        if optimizer:
            health_info[f"{prefix}optimizer"] = optimizer

        horizon_hours = coordinator.config.get(CONF_HORIZON_HOURS)
        if horizon_hours is not None:
            health_info[f"{prefix}horizon_hours"] = horizon_hours

        period_minutes = coordinator.config.get(CONF_PERIOD_MINUTES)
        if period_minutes is not None:
            health_info[f"{prefix}period_minutes"] = period_minutes

    return health_info
