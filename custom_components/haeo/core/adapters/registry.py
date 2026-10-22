"""Element adapter registry and model element collection."""

from collections.abc import Mapping
from typing import (
    Any,  # noqa: TID251  # ElementAdapter Protocol: each adapter's config/output types are narrower
    Protocol,
    TypeGuard,
    runtime_checkable,
)

from custom_components.haeo.core.adapters.elements.battery import adapter as battery_adapter
from custom_components.haeo.core.adapters.elements.battery_section import adapter as battery_section_adapter
from custom_components.haeo.core.adapters.elements.buffer import adapter as buffer_adapter
from custom_components.haeo.core.adapters.elements.connection import adapter as connection_adapter
from custom_components.haeo.core.adapters.elements.deferrable_load import adapter as deferrable_load_adapter
from custom_components.haeo.core.adapters.elements.ev import adapter as ev_adapter
from custom_components.haeo.core.adapters.elements.grid import adapter as grid_adapter
from custom_components.haeo.core.adapters.elements.inverter import adapter as inverter_adapter
from custom_components.haeo.core.adapters.elements.junction import adapter as junction_adapter
from custom_components.haeo.core.adapters.elements.load import adapter as load_adapter
from custom_components.haeo.core.adapters.elements.node import adapter as node_adapter
from custom_components.haeo.core.adapters.elements.policy import adapter as policy_adapter
from custom_components.haeo.core.adapters.elements.solar import adapter as solar_adapter
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName
from custom_components.haeo.core.model.elements import ELEMENTS
from custom_components.haeo.core.model.output_data import ModelOutputValue, OutputData
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.core.schema.elements.buffer import BufferRole


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

    can_source: bool

    can_sink: bool

    # Whether the element can be the switchboard: the central point other
    # elements connect to, which a hub outside advanced mode always has
    switchboard: bool

    @property
    def device_names(self) -> frozenset[str]:
        """Names of the devices the element creates."""
        ...

    # What a buffer can count the element as: a load it covers, generation
    # it covers, or storage that holds it
    buffer_roles: frozenset[BufferRole]

    def model_elements(self, config: Any) -> list[ModelElementConfig]:
        """Return model element parameters for the loaded config.

        Typed ``Any`` deliberately: each adapter implementation narrows this to its
        own concrete ``*ConfigData`` TypedDict (e.g. ``GridConfigData``,
        ``BatteryConfigData``). Protocol method parameters are contravariant, and
        those concrete types share no common non-trivial supertype narrower than
        ``object`` (which pyright rejects as incompatible with any of them), so
        ``Any`` is the only type under which every adapter structurally conforms.
        """
        ...

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[Any, Mapping[Any, OutputData]]:
        """Map model outputs to device-specific outputs.

        Typed ``Any`` deliberately: some adapters (grid, load, solar) add their own
        required keyword-only parameters (``config``, ``periods``) on top of
        ``**_kwargs``, which only conforms to a catch-all ``**_kwargs: object`` when
        the catch-all itself is ``Any`` (kwonly params are checked contravariantly
        against it). The return type's key positions are ``Any`` for a related
        reason: each adapter returns ``Mapping[ItsDeviceName, Mapping[ItsOutputName,
        OutputData]]`` with its own ``Literal`` name types, and ``Mapping``'s key
        type parameter is invariant, so no shared key type (not even ``str``) is
        compatible with every adapter's concrete return type.
        """
        ...


@runtime_checkable
class ConfiguredRolesAdapter(Protocol):
    """An adapter whose elements each choose in their config whether they produce or consume power.

    Such an element sources or sinks power only when its config says so, so
    can_source and can_sink only say what it may do.
    """

    def roles(self, config: Mapping[str, object]) -> tuple[bool, bool]:
        """Return whether the configured element can source and can sink power."""
        ...


ELEMENT_TYPES: dict[ElementType, ElementAdapter] = {
    ElementType.GRID: grid_adapter,
    ElementType.LOAD: load_adapter,
    ElementType.INVERTER: inverter_adapter,
    ElementType.SOLAR: solar_adapter,
    ElementType.BATTERY: battery_adapter,
    ElementType.DEFERRABLE_LOAD: deferrable_load_adapter,
    ElementType.EV: ev_adapter,
    ElementType.CONNECTION: connection_adapter,
    ElementType.JUNCTION: junction_adapter,
    ElementType.NODE: node_adapter,
    ElementType.BATTERY_SECTION: battery_section_adapter,
    ElementType.POLICY: policy_adapter,
    ElementType.BUFFER: buffer_adapter,
}


def is_element_type(value: object) -> TypeGuard[ElementType]:
    """Return True when value is a valid ElementType string.

    Use this to narrow untyped values (e.g., from dict.get()) to ElementType,
    enabling type-safe access to ELEMENT_TYPES and ELEMENT_CONFIG_SCHEMAS.
    Accepts both ElementType members and plain strings matching a member value.
    """
    return value in ELEMENT_TYPES


def collect_model_elements(
    participants: Mapping[str, ElementConfigData],
) -> list[ModelElementConfig]:
    """Collect and sort model elements from all participants."""
    all_model_elements: list[ModelElementConfig] = []
    for loaded_params in participants.values():
        element_type = loaded_params[CONF_ELEMENT_TYPE]
        model_elements = ELEMENT_TYPES[element_type].model_elements(loaded_params)
        all_model_elements.extend(model_elements)

    return sorted(all_model_elements, key=lambda e: ELEMENTS[e["element_type"]].add_order)


__all__ = [
    "ELEMENT_TYPES",
    "ConfiguredRolesAdapter",
    "ElementAdapter",
    "collect_model_elements",
    "is_element_type",
]
