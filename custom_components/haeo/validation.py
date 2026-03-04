"""Validation helpers for HAEO network topology."""

from collections.abc import Mapping, Sequence

from .core.const import CONF_ELEMENT_TYPE
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


def format_component_summary(components: Sequence[Sequence[str]], *, separator: str = "\n") -> str:
    """Create human-readable summary of disconnected components."""

    lines: list[str] = []
    for index, component in enumerate(components, start=1):
        names = ", ".join(component)
        lines.append(f"{index}) {names}")
    return separator.join(lines)


__all__ = [
    "NetworkConnectivityResult",
    "format_component_summary",
    "validate_network_topology",
]
