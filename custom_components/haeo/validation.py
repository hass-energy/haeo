"""Validation helpers for HAEO network topology."""

from collections.abc import Mapping, Sequence
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_ELEMENT_TYPE
from .elements import ELEMENT_TYPE_CONNECTION, ELEMENT_TYPES, ElementConfigSchema, collect_element_subentries
from .model import MODEL_ELEMENT_ENERGY_BALANCE_CONNECTION
from .util.forecast_times import generate_forecast_timestamps_from_config
from .util.graph import ConnectivityResult as NetworkConnectivityResult
from .util.graph import find_connected_components


def collect_participant_configs(entry: ConfigEntry) -> dict[str, ElementConfigSchema]:
    """Return a mutable copy of participant configurations for an entry."""

    participants: dict[str, ElementConfigSchema] = {}

    for subentry in collect_element_subentries(entry):
        participants[subentry.name] = subentry.config.copy()

    return participants


async def _build_adjacency(
    hass: HomeAssistant,
    participants: Mapping[str, ElementConfigSchema],
    forecast_times: Sequence[float],
) -> dict[str, set[str]]:
    """Build adjacency map by transforming configs through adapters.

    This uses the adapter layer to convert configuration elements into model elements,
    which includes both explicit connection elements and implicit connections.
    """
    adjacency: dict[str, set[str]] = {}

    # Collect all model elements from all configs
    for config in participants.values():
        element_type = config[CONF_ELEMENT_TYPE]
        entry = ELEMENT_TYPES[element_type]

        # Load config with actual forecast times to get real sensor data
        loaded = await entry.load(config, hass=hass, forecast_times=forecast_times)

        # Get model elements including implicit connections
        model_elements = entry.model_elements(loaded)

        # Add non-connection elements as nodes (skip balance connections - internal bookkeeping)
        for elem in model_elements:
            elem_type = elem.get(CONF_ELEMENT_TYPE)
            if elem_type not in {ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_ENERGY_BALANCE_CONNECTION}:
                adjacency.setdefault(elem["name"], set())

        # Add edges from connection elements
        for elem in model_elements:
            if elem.get(CONF_ELEMENT_TYPE) == ELEMENT_TYPE_CONNECTION:
                source: Any = elem["source"]
                target: Any = elem["target"]
                adjacency.setdefault(source, set()).add(target)
                adjacency.setdefault(target, set()).add(source)

    return adjacency


async def validate_network_topology(
    hass: HomeAssistant,
    participants: Mapping[str, ElementConfigSchema],
    config_entry: ConfigEntry,
) -> NetworkConnectivityResult:
    """Validate connectivity for the provided participant configurations.

    Uses the adapter layer to transform configurations into model elements,
    which automatically includes implicit connections created by elements.

    Args:
        hass: Home Assistant instance.
        participants: Map of element names to their configurations.
        config_entry: Config entry containing tier configuration for forecast times.

    Returns:
        NetworkConnectivityResult indicating connectivity status.

    """
    if not participants:
        return NetworkConnectivityResult(is_connected=True, components=())

    forecast_times = generate_forecast_timestamps_from_config(config_entry.data)
    adjacency = await _build_adjacency(hass, participants, forecast_times)
    return find_connected_components(adjacency)


def format_component_summary(components: Sequence[Sequence[str]], *, separator: str = "\n") -> str:
    """Create human-readable summary of disconnected components."""

    lines: list[str] = []
    for index, component in enumerate(components, start=1):
        names = ", ".join(component)
        lines.append(f"{index}) {names}")
    return separator.join(lines)


__all__ = [
    "NetworkConnectivityResult",
    "collect_participant_configs",
    "format_component_summary",
    "validate_network_topology",
]
