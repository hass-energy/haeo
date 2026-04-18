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

# Element types that represent external power sources/sinks.
_EXTERNAL_TYPES: Final[frozenset[ElementType]] = frozenset({ElementType.GRID})

# Element types whose power output is time-sensitive (must be consumed now).
_TIME_SENSITIVE_TYPES: Final[frozenset[ElementType]] = frozenset(
    {
        ElementType.SOLAR,
        ElementType.LOAD,
    }
)


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

    # Derive connection properties from endpoint element types
    name_to_type = {name: config[CONF_ELEMENT_TYPE] for name, config in participants.items()}
    for model_element in all_model_elements:
        if model_element.get("element_type") == MODEL_ELEMENT_TYPE_CONNECTION:
            conn = _as_connection_config(model_element)
            source_type = name_to_type.get(conn["source"])
            target_type = name_to_type.get(conn["target"])
            endpoint_types = {t for t in (source_type, target_type) if t is not None}
            conn["is_external"] = bool(endpoint_types & _EXTERNAL_TYPES)
            conn["is_time_sensitive"] = bool(endpoint_types & _TIME_SENSITIVE_TYPES)

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
