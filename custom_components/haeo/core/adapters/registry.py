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
from custom_components.haeo.core.adapters.elements.tariff import TariffAdapter
from custom_components.haeo.core.adapters.elements.tariff import adapter as tariff_adapter
from custom_components.haeo.core.adapters.tariff_compilation import compile_tariffs
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

    Tariff elements are handled specially: instead of producing model elements,
    their configs are extracted as tariff rules. After all other elements are
    collected, the tariff compilation step injects tags and scoped pricing
    segments into existing connections.
    """
    all_model_elements: list[ModelElementConfig] = []
    tariff_rules: list[dict[str, Any]] = []

    for loaded_params in participants.values():
        element_type = loaded_params[CONF_ELEMENT_TYPE]
        adapter = ELEMENT_TYPES[element_type]

        # Tariff adapters produce rules, not model elements
        if isinstance(adapter, TariffAdapter):
            tariff_rules.append(adapter.tariff_rule(loaded_params))
        else:
            model_elements = adapter.model_elements(loaded_params)
            all_model_elements.extend(model_elements)

    # Compile tariffs into tags and scoped segments on connections
    if tariff_rules:
        compiled = compile_tariffs(
            [dict(e) for e in all_model_elements],
            tariff_rules,
        )
        all_model_elements = compiled  # type: ignore[assignment]

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
