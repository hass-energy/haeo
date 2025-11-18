"""Diagnostics support for HAEO integration."""

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from .const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON_HOURS,
    CONF_PERIOD_MINUTES,
    CONF_UPDATE_INTERVAL_MINUTES,
    OPTIMIZATION_STATUS_PENDING,
)
from .coordinator import CoordinatorOutput, HaeoDataUpdateCoordinator
from .model import (
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
    OutputName,
)
from .validation import collect_participant_configs, validate_network_topology


def _get_hub_outputs(
    coordinator: HaeoDataUpdateCoordinator,
    config_entry: ConfigEntry,
) -> Mapping[OutputName, CoordinatorOutput]:
    """Return coordinator outputs for the hub element."""

    if not coordinator.data:
        return {}

    hub_title = config_entry.title or config_entry.entry_id
    hub_key = slugify(str(hub_title))
    return coordinator.data.get(hub_key, {})


def _get_output_state(
    outputs: Mapping[OutputName, CoordinatorOutput],
    output_name: OutputName,
) -> Any | None:
    """Extract the state value for a specific coordinator output."""

    output = outputs.get(output_name)
    return output.state if output and output.state is not None else None


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
    subentries_info: list[dict[str, Any]] = []
    for subentry in config_entry.subentries.values():
        raw_data = dict(subentry.data)
        name = raw_data.get("name")

        subentry_info: dict[str, Any] = {
            "subentry_id": subentry.subentry_id,
            "subentry_type": subentry.subentry_type,
            "title": subentry.title,
            "name": name,
        }

        if subentry.subentry_type != "network":
            raw_data.setdefault("name", name)
            raw_data.setdefault(CONF_ELEMENT_TYPE, subentry.subentry_type)
            subentry_info["config"] = raw_data

        subentries_info.append(subentry_info)

    diagnostics["subentries"] = subentries_info

    # Add coordinator state if available
    if coordinator:
        hub_outputs = _get_hub_outputs(coordinator, config_entry)
        optimization_status = _get_output_state(hub_outputs, OUTPUT_NAME_OPTIMIZATION_STATUS)
        optimization_cost = _get_output_state(hub_outputs, OUTPUT_NAME_OPTIMIZATION_COST)
        optimization_duration = _get_output_state(hub_outputs, OUTPUT_NAME_OPTIMIZATION_DURATION)
        last_update_time = getattr(coordinator, "last_update_success_time", None)

        diagnostics["coordinator"] = {
            "optimization_status": optimization_status or OPTIMIZATION_STATUS_PENDING,
            "last_update_success": coordinator.last_update_success,
            "update_interval": (coordinator.update_interval.total_seconds() if coordinator.update_interval else None),
        }

        if (
            last_update_time
            or optimization_status
            or optimization_cost is not None
            or optimization_duration is not None
        ):
            last_optimization: dict[str, Any] = {
                "status": optimization_status or OPTIMIZATION_STATUS_PENDING,
                "duration_seconds": optimization_duration,
                "cost": optimization_cost,
            }

            if last_update_time:
                last_optimization["timestamp"] = last_update_time.isoformat()

            diagnostics["last_optimization"] = last_optimization

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
            connection_pairs: list[dict[str, str]] = []
            for element_name, element in coordinator.network.elements.items():
                if element_name.startswith("connection_"):
                    source = getattr(element, "source", None)
                    target = getattr(element, "target", None)
                    if source and target:
                        connection_pairs.append({"from": source, "to": target})

            connectivity_result = validate_network_topology(collect_participant_configs(config_entry))
            connected_components = [list(component) for component in connectivity_result.components]

            network_info: dict[str, Any] = {
                "num_elements": len(coordinator.network.elements),
                "element_names": list(coordinator.network.elements.keys()),
                "connections": connection_pairs,
                "connectivity_check": connectivity_result.is_connected,
                "connected_components": connected_components,
                "num_components": len(connected_components),
            }

            diagnostics["network"] = network_info

    return diagnostics
