"""Diagnostics support for HAEO integration."""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.haeo.schema import unflatten

from .const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON_HOURS,
    CONF_PERIOD_MINUTES,
    CONF_UPDATE_INTERVAL_MINUTES,
)
from .coordinator import HaeoDataUpdateCoordinator
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
            CONF_UPDATE_INTERVAL_MINUTES: config_entry.data.get(CONF_UPDATE_INTERVAL_MINUTES),
            CONF_DEBOUNCE_SECONDS: config_entry.data.get(CONF_DEBOUNCE_SECONDS),
        },
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
            raw_data.setdefault("name", name)
            raw_data.setdefault(CONF_ELEMENT_TYPE, subentry.subentry_type)
            structured_config = unflatten(raw_data)
            subentry_info["config"] = structured_config

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

        # Summarize available outputs from the coordinator data
        if coordinator.data:
            outputs_summary: dict[str, Any] = {}
            for element_name, outputs in coordinator.data.items():
                element_summary: dict[str, Any] = {}
                for output_name, output in outputs.items():
                    forecast_points = len(output.forecast) if output.forecast else 0
                    element_summary[output_name] = {
                        "type": output.type,
                        "unit": output.unit,
                        "state": output.state,
                        "value_count": forecast_points or (1 if output.state is not None else 0),
                        "first_value": output.state if output.state is not None else None,
                        "has_forecast": bool(output.forecast),
                    }
                outputs_summary[element_name] = element_summary
            diagnostics["outputs"] = outputs_summary

        # Add network structure information when available
        if coordinator.network:
            connection_pairs = []
            for element_name, element in coordinator.network.elements.items():
                if element_name.startswith("connection_"):
                    source = getattr(element, "source", None)
                    target = getattr(element, "target", None)
                    if source and target:
                        connection_pairs.append({"from": source, "to": target})

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

    return diagnostics
