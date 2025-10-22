"""Diagnostics support for HAEO integration."""

from typing import Any, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.haeo.schema import unflatten

from .const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON_HOURS,
    CONF_OPTIMIZER,
    CONF_PERIOD_MINUTES,
    CONF_UPDATE_INTERVAL_MINUTES,
)
from .coordinator import HaeoDataUpdateCoordinator
from .elements import ELEMENT_TYPES, ElementType
from .validation import collect_participant_configs, validate_network_topology


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
            CONF_HORIZON_HOURS: config_entry.data.get(CONF_HORIZON_HOURS),
            CONF_PERIOD_MINUTES: config_entry.data.get(CONF_PERIOD_MINUTES),
            CONF_OPTIMIZER: config_entry.data.get(CONF_OPTIMIZER),
            CONF_UPDATE_INTERVAL_MINUTES: config_entry.data.get(CONF_UPDATE_INTERVAL_MINUTES),
            CONF_DEBOUNCE_SECONDS: config_entry.data.get(CONF_DEBOUNCE_SECONDS),
        },
        "elements": {},
    }

    # Add subentry information
    subentries_info = []
    for subentry in config_entry.subentries.values():
        raw_data = dict(subentry.data)
        name = raw_data.get("name")

        subentry_info = {
            "subentry_id": subentry.subentry_id,
            "subentry_type": subentry.subentry_type,
            "title": subentry.title,
            "name": name,
        }

        if subentry.subentry_type != "network":
            element_type = cast("ElementType", subentry.subentry_type)
            registry_entry = ELEMENT_TYPES.get(element_type)
            if registry_entry is not None:
                raw_data.setdefault("name", name)
                raw_data.setdefault(CONF_ELEMENT_TYPE, subentry.subentry_type)
                structured_config = unflatten(raw_data)
                subentry_info["config"] = structured_config
            else:
                subentry_info["config"] = raw_data

        subentries_info.append(subentry_info)

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

            network_info = {
                "num_elements": len(coordinator.network.elements),
                "element_names": list(coordinator.network.elements.keys()),
                "connections": connection_pairs,
            }

            connectivity_result = validate_network_topology(collect_participant_configs(config_entry))
            connected_components = [list(component) for component in connectivity_result.components]
            network_info["connectivity_check"] = connectivity_result.is_connected
            network_info["connected_components"] = connected_components
            network_info["num_components"] = len(connected_components)

            diagnostics["network"] = network_info

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
