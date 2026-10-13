"""Validation helpers for HAEO network topology."""

from collections.abc import Mapping, Sequence

from .core.const import CONF_ELEMENT_TYPE, CONF_NAME, ConnectivityLevel
from .core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION
from .elements import ELEMENT_TYPES, ElementConfigData
from .util.graph import ConnectivityResult as NetworkConnectivityResult
from .util.graph import find_connected_components


def _build_adjacency(participants: Mapping[str, ElementConfigData]) -> dict[str, set[str]]:
    """Build adjacency map from loaded element configs.

    Uses the adapter layer to convert loaded configs into model elements,
    which includes both explicit connection elements and implicit connections.
    """
    adjacency: dict[str, set[str]] = {}

    # Collect all model elements from all configs
    for loaded_config in participants.values():
        element_type = loaded_config[CONF_ELEMENT_TYPE]
        adapter = ELEMENT_TYPES[element_type]

        # Get model elements including implicit connections
        model_elements = adapter.model_elements(loaded_config)

        # Add non-connection elements as nodes (skip internal connection elements)
        for elem in model_elements:
            elem_type = elem["element_type"]
            if elem_type != MODEL_ELEMENT_TYPE_CONNECTION:
                adjacency.setdefault(elem["name"], set())

        # Add edges from connection elements
        for elem in model_elements:
            if elem["element_type"] != MODEL_ELEMENT_TYPE_CONNECTION:
                continue
            source = elem["source"]
            target = elem["target"]
            adjacency.setdefault(source, set()).add(target)
            adjacency.setdefault(target, set()).add(source)

    return adjacency


def validate_network_topology(participants: Mapping[str, ElementConfigData]) -> NetworkConnectivityResult:
    """Validate connectivity for the provided participant configurations.

    Uses the adapter layer to transform loaded configs into model elements,
    which automatically includes implicit connections created by elements.

    Args:
        participants: Map of element names to their loaded configurations.

    Returns:
        NetworkConnectivityResult indicating connectivity status.

    """
    if not participants:
        return NetworkConnectivityResult(is_connected=True, components=())

    adjacency = _build_adjacency(participants)
    return find_connected_components(adjacency)


def find_invalid_connection_endpoints(participants: Mapping[str, ElementConfigData]) -> dict[str, tuple[str, ...]]:
    """Find elements that connect to an element which cannot be a connection endpoint.

    An element whose adapter has ``ConnectivityLevel.NEVER`` owns the connections that
    carry its limits, prices, and efficiencies.
    A connection made directly to such an element bypasses them, so it is invalid.
    Endpoints are read from the model connections each adapter produces, so every
    element type is checked the same way.

    Args:
        participants: Map of element names to their loaded configurations.

    Returns:
        Map of element name to the sorted names of the invalid endpoints it connects to.

    """
    closed = {
        config[CONF_NAME]
        for config in participants.values()
        if ELEMENT_TYPES[config[CONF_ELEMENT_TYPE]].connectivity == ConnectivityLevel.NEVER
    }

    invalid: dict[str, tuple[str, ...]] = {}
    for config in participants.values():
        name = config[CONF_NAME]
        adapter = ELEMENT_TYPES[config[CONF_ELEMENT_TYPE]]
        endpoints = {
            endpoint
            for elem in adapter.model_elements(config)
            if elem["element_type"] == MODEL_ELEMENT_TYPE_CONNECTION
            for endpoint in (elem["source"], elem["target"])
            if endpoint != name and endpoint in closed
        }
        if endpoints:
            invalid[name] = tuple(sorted(endpoints))
    return invalid


def format_component_summary(components: Sequence[Sequence[str]], *, separator: str = "\n") -> str:
    """Create human-readable summary of disconnected components."""

    lines: list[str] = []
    for index, component in enumerate(components, start=1):
        names = ", ".join(component)
        lines.append(f"{index}) {names}")
    return separator.join(lines)


__all__ = [
    "NetworkConnectivityResult",
    "find_invalid_connection_endpoints",
    "format_component_summary",
    "validate_network_topology",
]
