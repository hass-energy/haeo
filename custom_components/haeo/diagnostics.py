"""Diagnostics support for HAEO integration."""

from collections.abc import Mapping
from typing import Any, get_type_hints

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
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
from .elements import ELEMENT_TYPES, ElementConfigSchema
from .model import (
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
    OutputName,
)
from .schema import get_field_meta
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


def _collect_entity_ids(value: Any) -> set[str]:
    """Recursively collect entity IDs from nested configuration values.

    Note: This function is duplicated from coordinator.py to keep diagnostics
    independent from coordinator internals. The coordinator version uses Sequence
    while this uses list for simplicity, but they are functionally equivalent.
    """
    if isinstance(value, str):
        return {value}

    if isinstance(value, Mapping):
        mapping_ids: set[str] = set()
        for nested in value.values():
            mapping_ids.update(_collect_entity_ids(nested))
        return mapping_ids

    if isinstance(value, list):
        sequence_ids: set[str] = set()
        for nested in value:
            sequence_ids.update(_collect_entity_ids(nested))
        return sequence_ids

    return set()


def _extract_entity_ids_from_config(config: ElementConfigSchema) -> set[str]:
    """Extract entity IDs from a configuration using schema loaders.

    Note: This function is duplicated from coordinator.py to keep diagnostics
    independent from coordinator internals.
    """
    entity_ids: set[str] = set()

    element_type = config["element_type"]
    data_config_class = ELEMENT_TYPES[element_type].data
    hints = get_type_hints(data_config_class, include_extras=True)

    for field_name in hints:
        if field_name in ("element_type", "name"):
            continue

        field_value = config.get(field_name)
        if field_value is None:
            continue

        field_meta = get_field_meta(field_name, data_config_class)
        if field_meta is None:
            continue

        if field_meta.field_type == "constant":
            continue

        try:
            entity_ids.update(_collect_entity_ids(field_value))
        except TypeError:
            continue

    return entity_ids


def _state_to_dict(state: State) -> dict[str, Any]:
    """Convert a Home Assistant State object to a dictionary for scenario format."""
    return {
        "entity_id": state.entity_id,
        "state": state.state,
        "attributes": dict(state.attributes),
        "last_changed": state.last_changed.isoformat(),
        "last_reported": state.last_reported.isoformat(),
        "last_updated": state.last_updated.isoformat(),
        "context": {
            "id": state.context.id,
            "parent_id": state.context.parent_id,
            "user_id": state.context.user_id,
        },
    }


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

    # Add scenario-compatible format for easy test scenario creation
    scenario_config: dict[str, Any] = {
        "participants": {},
        CONF_HORIZON_HOURS: config_entry.data.get(CONF_HORIZON_HOURS),
        CONF_PERIOD_MINUTES: config_entry.data.get(CONF_PERIOD_MINUTES),
    }

    # Transform subentries into participants dict
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "network":
            raw_data = dict(subentry.data)
            raw_data.setdefault("name", subentry.title)
            raw_data.setdefault(CONF_ELEMENT_TYPE, subentry.subentry_type)
            scenario_config["participants"][subentry.title] = raw_data

    # Collect sensor states for all entities used in the configuration
    all_entity_ids: set[str] = set()
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "network":
            config = dict(subentry.data)
            config.setdefault(CONF_ELEMENT_TYPE, subentry.subentry_type)
            all_entity_ids.update(_extract_entity_ids_from_config(config))

    # Extract states for all collected entity IDs (input sensors)
    scenario_states: list[dict[str, Any]] = []
    for entity_id in sorted(all_entity_ids):
        state = _hass.states.get(entity_id)
        if state is not None:
            scenario_states.append(_state_to_dict(state))

    # Also collect output sensor states if coordinator has data (for diagnostics)
    output_states: list[dict[str, Any]] = []
    if coordinator and coordinator.data:
        # Create lookup dict to avoid O(n*m*k) complexity
        subentry_by_slug = {slugify(subentry.title): subentry for subentry in config_entry.subentries.values()}

        for element_key, outputs in coordinator.data.items():
            subentry = subentry_by_slug.get(element_key)
            if subentry:
                for output_name in outputs:
                    unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{output_name}"
                    entity_id = f"sensor.{config_entry.domain}_{unique_id}"
                    state = _hass.states.get(entity_id)
                    if state is not None:
                        output_states.append(_state_to_dict(state))

    # Add the scenario format section
    diagnostics["scenario_format"] = {
        "config": scenario_config,
        "states": scenario_states,
        "output_states": output_states if output_states else None,
    }

    return diagnostics
