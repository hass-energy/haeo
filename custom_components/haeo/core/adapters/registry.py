"""Element adapter registry and model element collection."""

from collections.abc import Mapping
from typing import Any, Protocol, TypeGuard, runtime_checkable

from custom_components.haeo.core.adapters.elements.battery import adapter as battery_adapter
from custom_components.haeo.core.adapters.elements.battery_section import adapter as battery_section_adapter
from custom_components.haeo.core.adapters.elements.connection import adapter as connection_adapter
from custom_components.haeo.core.adapters.elements.grid import adapter as grid_adapter
from custom_components.haeo.core.adapters.elements.inverter import adapter as inverter_adapter
from custom_components.haeo.core.adapters.elements.load import adapter as load_adapter
from custom_components.haeo.core.adapters.elements.node import adapter as node_adapter
from custom_components.haeo.core.adapters.elements.solar import adapter as solar_adapter
from custom_components.haeo.core.adapters.elements.tariff import adapter as tariff_adapter
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName
from custom_components.haeo.core.model.output_data import ModelOutputValue, OutputData
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType


@runtime_checkable
class ElementAdapter(Protocol):
    """Protocol for element adapters.

    Each element type provides an adapter that bridges configuration
    with the LP model layer. Adapters must implement this protocol
    and be registered in the ELEMENT_TYPES registry.
    """

    element_type: str

    advanced: bool

    connectivity: ConnectivityLevel

    def model_elements(self, config: Any) -> list[ModelElementConfig]:
        """Return model element parameters for the loaded config."""
        ...

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[Any, Mapping[Any, OutputData]]:
        """Map model outputs to device-specific outputs."""
        ...


ELEMENT_TYPES: dict[ElementType, ElementAdapter] = {
    ElementType.GRID: grid_adapter,
    ElementType.LOAD: load_adapter,
    ElementType.INVERTER: inverter_adapter,
    ElementType.SOLAR: solar_adapter,
    ElementType.BATTERY: battery_adapter,
    ElementType.CONNECTION: connection_adapter,
    ElementType.NODE: node_adapter,
    ElementType.BATTERY_SECTION: battery_section_adapter,
    ElementType.TARIFF: tariff_adapter,
}


def is_element_type(value: Any) -> TypeGuard[ElementType]:
    """Return True when value is a valid ElementType string.

    Use this to narrow Any values (e.g., from dict.get()) to ElementType,
    enabling type-safe access to ELEMENT_TYPES and ELEMENT_CONFIG_SCHEMAS.
    Accepts both ElementType members and plain strings matching a member value.
    """
    return value in ELEMENT_TYPES


def collect_model_elements(
    participants: Mapping[str, ElementConfigData],
) -> list[ModelElementConfig]:
    """Collect and sort model elements from all participants.

    Tariff elements produce connection configs that get merged into existing
    connections between the same endpoints. The merge adds tags and tag-scoped
    segments to the existing connection rather than creating a parallel one.
    """
    all_model_elements: list[ModelElementConfig] = []
    for loaded_params in participants.values():
        element_type = loaded_params[CONF_ELEMENT_TYPE]
        model_elements = ELEMENT_TYPES[element_type].model_elements(loaded_params)
        all_model_elements.extend(model_elements)

    # Merge tariff connections into existing connections
    all_model_elements = _merge_tariff_connections(all_model_elements)

    return sorted(
        all_model_elements,
        key=lambda e: e.get("element_type") == ElementType.CONNECTION,
    )


def _merge_tariff_connections(
    elements: list[ModelElementConfig],
) -> list[ModelElementConfig]:
    """Merge tariff-generated connections into existing connections.

    Finds connection configs that share the same source/target endpoints.
    When a tariff connection (one with tags > [0]) targets the same node pair
    as an existing connection, merge the tariff's tags and tag-scoped segments
    into the existing connection.
    """
    from custom_components.haeo.core.model.elements.connection import (  # noqa: PLC0415
        ConnectionElementConfig,
    )
    from custom_components.haeo.core.model.elements.segments.segment import DEFAULT_TAG  # noqa: PLC0415

    # Separate connections from other elements
    connections: list[dict[str, Any]] = []
    non_connections: list[ModelElementConfig] = []

    for elem in elements:
        if elem.get("element_type") == "connection":
            # Work with mutable copies
            connections.append(dict(elem))
        else:
            non_connections.append(elem)

    if len(connections) <= 1:
        return [*non_connections, *connections]

    # Index connections by (source, target) endpoint pair
    # A tariff connection is one with extra tags beyond DEFAULT_TAG
    base_connections: dict[tuple[str, str], dict[str, Any]] = {}
    tariff_connections: list[dict[str, Any]] = []

    for conn in connections:
        source = conn.get("source", "")
        target = conn.get("target", "")
        tags = conn.get("tags", [])
        has_extra_tags = any(t != DEFAULT_TAG for t in tags)

        if has_extra_tags:
            tariff_connections.append(conn)
        else:
            pair = (source, target)
            base_connections[pair] = conn

    # Merge tariff connections into base connections
    merged_tariffs: list[dict[str, Any]] = []
    for tariff_conn in tariff_connections:
        source = tariff_conn.get("source", "")
        target = tariff_conn.get("target", "")

        # Look for existing connection in either direction
        base = base_connections.get((source, target)) or base_connections.get((target, source))

        if base is not None:
            # Merge tags — ensure DEFAULT_TAG is present
            base_tags: list[int] = list(base.get("tags", [DEFAULT_TAG]))
            if DEFAULT_TAG not in base_tags:
                base_tags.insert(0, DEFAULT_TAG)
            tariff_tags: list[int] = list(tariff_conn.get("tags", []))
            for tag in tariff_tags:
                if tag not in base_tags:
                    base_tags.append(tag)
            base["tags"] = base_tags

            # Merge segments (add tariff's tag-scoped segments)
            base_segments: dict[str, Any] = dict(base.get("segments", {}))
            tariff_segments: dict[str, Any] = dict(tariff_conn.get("segments", {}))
            for seg_name, seg_spec in tariff_segments.items():
                # Only merge tag-scoped segments (those with a tag field)
                if seg_spec.get("tag") is not None:
                    # Ensure unique segment names
                    merged_name = seg_name
                    counter = 0
                    while merged_name in base_segments:
                        counter += 1
                        merged_name = f"{seg_name}_{counter}"
                    base_segments[merged_name] = seg_spec
            base["segments"] = base_segments
        else:
            # No matching base connection — keep as standalone
            merged_tariffs.append(tariff_conn)

    result_connections = list(base_connections.values()) + merged_tariffs
    return [*non_connections, *result_connections]


__all__ = [
    "ELEMENT_TYPES",
    "ElementAdapter",
    "collect_model_elements",
    "is_element_type",
]
