"""Element adapter registry and model element collection."""

from collections.abc import Mapping
from typing import Any, Final, Protocol, TypeGuard, runtime_checkable

from custom_components.haeo.core.adapters.elements.battery import adapter as battery_adapter
from custom_components.haeo.core.adapters.elements.battery_section import adapter as battery_section_adapter
from custom_components.haeo.core.adapters.elements.connection import adapter as connection_adapter
from custom_components.haeo.core.adapters.elements.grid import adapter as grid_adapter
from custom_components.haeo.core.adapters.elements.inverter import adapter as inverter_adapter
from custom_components.haeo.core.adapters.elements.load import adapter as load_adapter
from custom_components.haeo.core.adapters.elements.node import adapter as node_adapter
from custom_components.haeo.core.adapters.elements.policy import adapter as policy_adapter
from custom_components.haeo.core.adapters.elements.solar import adapter as solar_adapter
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION
from custom_components.haeo.core.model.elements.connection import ConnectionElementConfig
from custom_components.haeo.core.model.output_data import ModelOutputValue, OutputData
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType

# Time preference priority for (element_type, direction) pairs.
# Lower values are preferred by the solver when breaking ties.
# Direction is relative to the element: "out" = power leaves, "in" = power enters.
_ENDPOINT_PRIORITY: Final[dict[tuple[ElementType, str], int]] = {
    (ElementType.LOAD, "in"): 0,
    (ElementType.SOLAR, "out"): 1,
    (ElementType.BATTERY, "in"): 2,
    (ElementType.GRID, "in"): 3,
    (ElementType.BATTERY, "out"): 4,
    (ElementType.GRID, "out"): 5,
    (ElementType.INVERTER, "out"): 6,
    (ElementType.INVERTER, "in"): 7,
}

_DEFAULT_PRIORITY: Final = max(_ENDPOINT_PRIORITY.values()) + 1


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
    ElementType.POLICY: policy_adapter,
}


def is_element_type(value: Any) -> TypeGuard[ElementType]:
    """Return True when value is a valid ElementType string.

    Use this to narrow Any values (e.g., from dict.get()) to ElementType,
    enabling type-safe access to ELEMENT_TYPES and ELEMENT_CONFIG_SCHEMAS.
    Accepts both ElementType members and plain strings matching a member value.
    """
    return value in ELEMENT_TYPES


def _as_connection_config(config: ModelElementConfig) -> ConnectionElementConfig:
    """Narrow a model element config to ConnectionElementConfig."""
    return config  # type: ignore[return-value]


def collect_model_elements(
    participants: Mapping[str, ElementConfigData],
) -> list[ModelElementConfig]:
    """Collect and sort model elements from all participants."""
    all_model_elements: list[ModelElementConfig] = []
    for loaded_params in participants.values():
        element_type = loaded_params[CONF_ELEMENT_TYPE]
        model_elements = ELEMENT_TYPES[element_type].model_elements(loaded_params)
        all_model_elements.extend(model_elements)

    # Auto-compute connection priorities from endpoint element types
    name_to_type = {name: config[CONF_ELEMENT_TYPE] for name, config in participants.items()}
    for model_element in all_model_elements:
        if model_element.get("element_type") == MODEL_ELEMENT_TYPE_CONNECTION:
            conn = _as_connection_config(model_element)
            source_type = name_to_type.get(conn["source"])
            target_type = name_to_type.get(conn["target"])
            source_pri = (
                _ENDPOINT_PRIORITY.get((source_type, "out"), _DEFAULT_PRIORITY) if source_type else _DEFAULT_PRIORITY
            )
            target_pri = (
                _ENDPOINT_PRIORITY.get((target_type, "in"), _DEFAULT_PRIORITY) if target_type else _DEFAULT_PRIORITY
            )
            conn["priority"] = min(source_pri, target_pri)

    return sorted(
        all_model_elements,
        key=lambda e: e.get("element_type") == ElementType.CONNECTION,
    )


__all__ = [
    "ELEMENT_TYPES",
    "ElementAdapter",
    "collect_model_elements",
    "is_element_type",
]
