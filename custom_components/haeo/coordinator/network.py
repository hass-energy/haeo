"""Network building and connectivity helpers for the HAEO integration."""

from collections.abc import Mapping, Sequence
import contextlib
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.elements import (
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPES,
    ElementConfigData,
    ElementConfigSchema,
)
from custom_components.haeo.model import Network
from custom_components.haeo.repairs import create_disconnected_network_issue, dismiss_disconnected_network_issue
from custom_components.haeo.validation import (
    collect_participant_configs,
    format_component_summary,
    validate_network_topology,
)

_LOGGER = logging.getLogger(__name__)


def _collect_model_elements(
    participants: Mapping[str, ElementConfigData],
) -> list[dict[str, Any]]:
    """Collect and sort model elements from all participants."""
    all_model_elements: list[dict[str, Any]] = []
    for loaded_params in participants.values():
        element_type = loaded_params[CONF_ELEMENT_TYPE]
        model_elements = ELEMENT_TYPES[element_type].model_elements(loaded_params)
        all_model_elements.extend(model_elements)

    # Sort so connections are added last
    return sorted(
        all_model_elements,
        key=lambda e: e.get("element_type") == ELEMENT_TYPE_CONNECTION,
    )


async def create_network(
    entry: ConfigEntry,
    *,
    periods_seconds: Sequence[int],
    participants: Mapping[str, ElementConfigData],
) -> Network:
    """Create a new Network from configuration."""
    # Convert seconds to hours for model layer
    periods_hours = [s / 3600 for s in periods_seconds]
    net = Network(name=f"haeo_network_{entry.entry_id}", periods=periods_hours)

    if not participants:
        _LOGGER.info("No participants configured for hub - returning empty network")
        return net

    sorted_model_elements = _collect_model_elements(participants)

    for model_element_config in sorted_model_elements:
        element_name = model_element_config.get("name")
        try:
            net.add(**model_element_config)
        except Exception as e:
            msg = f"Failed to add model element '{element_name}' (type={model_element_config.get('element_type')})"
            _LOGGER.exception(msg)
            raise ValueError(msg) from e

    return net


def update_element(
    network: Network,
    element_config: ElementConfigData,
) -> None:
    """Update TrackedParams for a single element in the network."""
    element_type = element_config[CONF_ELEMENT_TYPE]
    model_elements = ELEMENT_TYPES[element_type].model_elements(element_config)

    for model_element_config in model_elements:
        element_name = model_element_config.get("name")

        if element_name not in network.elements:
            _LOGGER.warning(
                "Model element '%s' not found in network during update - skipping",
                element_name,
            )
            continue

        element = network.elements[element_name]
        for param_name, param_value in model_element_config.items():
            with contextlib.suppress(KeyError):
                element[param_name] = param_value


async def evaluate_network_connectivity(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    participant_configs: Mapping[str, ElementConfigSchema] | None = None,
) -> None:
    """Validate the network connectivity for an entry and manage repair issues."""

    participants = dict(participant_configs) if participant_configs is not None else collect_participant_configs(entry)
    result = await validate_network_topology(hass, participants, entry)

    if result.is_connected:
        dismiss_disconnected_network_issue(hass, entry.entry_id)
        return

    create_disconnected_network_issue(hass, entry.entry_id, result.components)

    summary = format_component_summary(result.components, separator=" | ")
    _LOGGER.warning(
        "Network %s has %d disconnected component(s): %s",
        entry.entry_id,
        result.num_components,
        summary or "no components",
    )


__all__ = [
    "create_network",
    "evaluate_network_connectivity",
    "update_element",
]
