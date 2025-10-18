"""Diagnostics support for HAEO integration."""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_HORIZON_HOURS, CONF_OPTIMIZER, CONF_PERIOD_MINUTES
from .coordinator import HaeoDataUpdateCoordinator


async def async_get_config_entry_diagnostics(_hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a HAEO config entry."""
    coordinator: HaeoDataUpdateCoordinator | None = config_entry.runtime_data

    diagnostics: dict[str, Any] = {
        "config_entry": {
            "entry_id": config_entry.entry_id,
            "title": config_entry.title,
            "version": config_entry.version,
            "domain": config_entry.domain,
        },
        "hub_config": {
            "horizon_hours": config_entry.data.get(CONF_HORIZON_HOURS),
            "period_minutes": config_entry.data.get(CONF_PERIOD_MINUTES),
            "optimizer": config_entry.data.get(CONF_OPTIMIZER),
        },
        "elements": {},
    }

    # Add subentry information
    subentries_info = []
    for subentry in config_entry.subentries.values():
        subentry_data = {
            "subentry_id": subentry.subentry_id,
            "subentry_type": subentry.subentry_type,
            "title": subentry.title,
            "name": subentry.data.get("name_value"),
        }

        # Add element-specific configuration (excluding sensitive data)
        if subentry.subentry_type != "network":
            element_config = dict(subentry.data)
            # Remove internal metadata
            element_config.pop("name_value", None)
            subentry_data["config"] = element_config

        subentries_info.append(subentry_data)

    diagnostics["subentries"] = subentries_info

    # Add coordinator state if available
    if coordinator:
        diagnostics["coordinator"] = {
            "optimization_status": coordinator.optimization_status,
            "last_update_success": coordinator.last_update_success,
            "update_interval": (coordinator.update_interval.total_seconds() if coordinator.update_interval else None),
        }

        # Add optimization result summary
        if coordinator.last_optimization_time:
            diagnostics["last_optimization"] = {
                "timestamp": coordinator.last_optimization_time.isoformat(),
                "status": coordinator.optimization_status,
                "duration_seconds": coordinator.last_optimization_duration,
                "cost": coordinator.last_optimization_cost,
            }

        # Add network structure information
        if coordinator.network:
            # Get connection elements
            connection_pairs = []
            for element_name, element in coordinator.network.elements.items():
                if element_name.startswith("connection_"):
                    # Extract from/to from connection elements using getattr for type safety
                    source = getattr(element, "source", None)
                    target = getattr(element, "target", None)
                    if source and target:
                        connection_pairs.append(
                            {
                                "from": source,
                                "to": target,
                            }
                        )

            diagnostics["network"] = {
                "num_elements": len(coordinator.network.elements),
                "element_names": list(coordinator.network.elements.keys()),
                "connections": connection_pairs,
            }

            # Add element-level optimization results
            if coordinator.optimization_result:
                element_results: dict[str, dict[str, Any]] = {}
                for element_name in coordinator.network.elements:
                    # Skip connection elements in results
                    if element_name.startswith("connection_"):
                        continue

                    try:
                        element_data = coordinator.get_element_data(element_name)
                        if element_data:
                            # Only include summary stats, not full time series
                            element_results[element_name] = {
                                "has_power_data": "power" in element_data,
                                "has_energy_data": "energy" in element_data,
                                "has_soc_data": "soc" in element_data,
                                "num_periods": (len(element_data.get("power", [])) if "power" in element_data else 0),
                            }
                    except Exception:
                        element_results[element_name] = {"error": "Failed to retrieve data"}

                diagnostics["optimization_results"] = element_results

    return diagnostics
