"""System health diagnostics for HAEO integration."""

from typing import Any

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, OPTIMIZATION_STATUS_FAILED, OPTIMIZATION_STATUS_PENDING, OPTIMIZATION_STATUS_SUCCESS
from .model.connection import Connection


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

        # Network status
        if coordinator.network is None:
            health_info[f"{prefix}network"] = "not_built"
            health_info[f"{prefix}optimization_status"] = coordinator.optimization_status
            continue

        # Validate network and report status
        try:
            coordinator.network.validate()
            health_info[f"{prefix}network"] = "valid"
        except ValueError as err:
            health_info[f"{prefix}network"] = f"invalid: {err}"

        # Network metrics
        network = coordinator.network
        total_elements = len(network.elements)
        connections = sum(1 for element in network.elements.values() if isinstance(element, Connection))
        non_connection_elements = total_elements - connections

        health_info[f"{prefix}elements"] = non_connection_elements
        health_info[f"{prefix}connections"] = connections

        # Optimization status
        status = coordinator.optimization_status
        if status == OPTIMIZATION_STATUS_SUCCESS:
            health_info[f"{prefix}optimization_status"] = "success"
        elif status == OPTIMIZATION_STATUS_PENDING:
            health_info[f"{prefix}optimization_status"] = "pending"
        elif status == OPTIMIZATION_STATUS_FAILED:
            health_info[f"{prefix}optimization_status"] = "failed"
        else:
            health_info[f"{prefix}optimization_status"] = f"unknown: {status}"

        # Optimization result details
        if coordinator.optimization_result:
            result = coordinator.optimization_result
            cost = result.get("cost")
            health_info[f"{prefix}last_optimization_cost"] = f"{cost:.2f}" if cost is not None else "none"

            duration = result.get("duration")
            health_info[f"{prefix}last_optimization_duration"] = f"{duration:.3f}s" if duration is not None else "none"

            timestamp = result.get("timestamp")
            health_info[f"{prefix}last_optimization_time"] = timestamp.isoformat() if timestamp else "none"

        # Optimizer configuration
        optimizer = coordinator.config.get("optimizer", "unknown")
        health_info[f"{prefix}optimizer"] = optimizer

        # Timing configuration
        horizon_hours = coordinator.config.get("horizon_hours", "unknown")
        period_minutes = coordinator.config.get("period_minutes", "unknown")
        health_info[f"{prefix}horizon_hours"] = horizon_hours
        health_info[f"{prefix}period_minutes"] = period_minutes

        # Entity availability check
        sensors_available, unavailable_sensors = coordinator.check_sensors_available()
        if sensors_available:
            health_info[f"{prefix}sensors"] = "all_available"
        else:
            health_info[f"{prefix}sensors"] = f"{len(unavailable_sensors)}_unavailable"
            # List first few unavailable sensors
            if unavailable_sensors:
                health_info[f"{prefix}unavailable_sensors"] = ", ".join(unavailable_sensors[:5])

    return health_info
