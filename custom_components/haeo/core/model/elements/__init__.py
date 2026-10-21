"""HAEO model elements.

This module re-exports all element classes for convenient imports.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Final, TypeGuard

from custom_components.haeo.core.model.element import NetworkElement

from .battery import BATTERY_OUTPUT_NAMES as BATTERY_OUTPUT_NAMES
from .battery import BATTERY_POWER_CONSTRAINTS as BATTERY_POWER_CONSTRAINTS
from .battery import ELEMENT_TYPE as MODEL_ELEMENT_TYPE_BATTERY
from .battery import Battery as Battery
from .battery import BatteryConstraintName as BatteryConstraintName
from .battery import BatteryElementConfig as BatteryElementConfig
from .battery import BatteryElementTypeName as BatteryElementTypeName
from .battery import BatteryOutputName as BatteryOutputName
from .buffer import BUFFER_OUTPUT_NAMES as BUFFER_OUTPUT_NAMES
from .buffer import ELEMENT_TYPE as MODEL_ELEMENT_TYPE_BUFFER
from .buffer import Buffer as Buffer
from .buffer import BufferElementConfig as BufferElementConfig
from .buffer import BufferElementTypeName as BufferElementTypeName
from .buffer import BufferOutputName as BufferOutputName
from .buffer import buffer_arguments
from .connection import CONNECTION_OUTPUT_NAMES as CONNECTION_OUTPUT_NAMES
from .connection import CONNECTION_POWER as CONNECTION_POWER
from .connection import ELEMENT_TYPE as MODEL_ELEMENT_TYPE_CONNECTION
from .connection import Connection as Connection
from .connection import ConnectionElementConfig as ConnectionElementConfig
from .connection import ConnectionElementTypeName as ConnectionElementTypeName
from .connection import ConnectionOutputName as ConnectionOutputName
from .deferrable_load import DEFERRABLE_LOAD_OUTPUT_NAMES as DEFERRABLE_LOAD_OUTPUT_NAMES
from .deferrable_load import ELEMENT_TYPE as MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD
from .deferrable_load import DeferrableLoad as DeferrableLoad
from .deferrable_load import DeferrableLoadConstraintName as DeferrableLoadConstraintName
from .deferrable_load import DeferrableLoadElementConfig as DeferrableLoadElementConfig
from .deferrable_load import DeferrableLoadElementTypeName as DeferrableLoadElementTypeName
from .deferrable_load import DeferrableLoadOutputName as DeferrableLoadOutputName
from .node import ELEMENT_TYPE as MODEL_ELEMENT_TYPE_NODE
from .node import NODE_OUTPUT_NAMES
from .node import Node as Node
from .node import NodeElementConfig as NodeElementConfig
from .node import NodeElementTypeName as NodeElementTypeName
from .node import NodeOutputName as NodeOutputName
from .policy_pricing import ELEMENT_TYPE as MODEL_ELEMENT_TYPE_POLICY_PRICING
from .policy_pricing import POLICY_PRICING_OUTPUT_NAMES as POLICY_PRICING_OUTPUT_NAMES
from .policy_pricing import PolicyPricing as PolicyPricing
from .policy_pricing import PolicyPricingElementConfig as PolicyPricingElementConfig
from .policy_pricing import PolicyPricingElementTypeName as PolicyPricingElementTypeName
from .policy_pricing import PolicyPricingTerm as PolicyPricingTerm
from .policy_pricing import policy_pricing_arguments
from .segments import EfficiencySegment as EfficiencySegment
from .segments import PassthroughSegment as PassthroughSegment
from .segments import PowerLimitSegment as PowerLimitSegment
from .segments import PricingSegment as PricingSegment
from .segments import Segment as Segment
from .segments import SegmentSpec as SegmentSpec
from .segments import SegmentType as SegmentType

# Type for all model element types
ModelElementType = (
    BatteryElementTypeName
    | NodeElementTypeName
    | ConnectionElementTypeName
    | PolicyPricingElementTypeName
    | BufferElementTypeName
    | DeferrableLoadElementTypeName
)

# Typed configs for all model elements (discriminated by element_type)
ModelElementConfig = (
    BatteryElementConfig
    | NodeElementConfig
    | ConnectionElementConfig
    | PolicyPricingElementConfig
    | BufferElementConfig
    | DeferrableLoadElementConfig
)

# Configs of the elements that produce or consume power themselves, which
# connections join and power balance applies to
type NetworkElementConfig = BatteryElementConfig | NodeElementConfig | DeferrableLoadElementConfig

# Configs of the network elements that may produce power, which take outbound tags
type SourceElementConfig = BatteryElementConfig | NodeElementConfig


def config_arguments(config: Mapping[str, object], _elements: Mapping[str, object]) -> dict[str, object]:
    """Return a config's fields other than its type and name, as an element's constructor arguments."""
    return {key: value for key, value in config.items() if key not in ("element_type", "name")}


@dataclass(frozen=True, slots=True)
class ElementSpec:
    """Specification for a model element type.

    Attributes:
        factory: The element class.
        output_names: The outputs the element reports.
        add_order: When the element is added to a network. Elements that produce
            or consume power come first, then the connections that join them,
            then the elements that read their flows.
        arguments: Builds the constructor arguments from a config and the
            elements already in the network, resolving any it refers to by name.

    """

    factory: type
    output_names: frozenset[str]
    add_order: int
    arguments: Callable[..., dict[str, object]] = config_arguments


# Registry of all model element types.
# Keys are element type strings used by Network.add().
ELEMENTS: Final[dict[ModelElementType, ElementSpec]] = {
    MODEL_ELEMENT_TYPE_BATTERY: ElementSpec(factory=Battery, output_names=BATTERY_OUTPUT_NAMES, add_order=0),
    MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD: ElementSpec(
        factory=DeferrableLoad, output_names=DEFERRABLE_LOAD_OUTPUT_NAMES, add_order=0
    ),
    MODEL_ELEMENT_TYPE_NODE: ElementSpec(factory=Node, output_names=NODE_OUTPUT_NAMES, add_order=0),
    MODEL_ELEMENT_TYPE_CONNECTION: ElementSpec(factory=Connection, output_names=CONNECTION_OUTPUT_NAMES, add_order=1),
    MODEL_ELEMENT_TYPE_BUFFER: ElementSpec(
        factory=Buffer, output_names=BUFFER_OUTPUT_NAMES, add_order=2, arguments=buffer_arguments
    ),
    MODEL_ELEMENT_TYPE_POLICY_PRICING: ElementSpec(
        factory=PolicyPricing,
        output_names=POLICY_PRICING_OUTPUT_NAMES,
        add_order=2,
        arguments=policy_pricing_arguments,
    ),
}


def is_network_element_config(config: ModelElementConfig) -> TypeGuard[NetworkElementConfig]:
    """Return whether a config builds a network element, one that produces or consumes power itself."""
    return issubclass(ELEMENTS[config["element_type"]].factory, NetworkElement)


def is_source_element_config(config: NetworkElementConfig) -> TypeGuard[SourceElementConfig]:
    """Return whether a network element may produce power, so it takes outbound tags; it may unless declared not to."""
    return config.get("is_source", True)


__all__ = [
    "BATTERY_OUTPUT_NAMES",
    "BATTERY_POWER_CONSTRAINTS",
    "BUFFER_OUTPUT_NAMES",
    "CONNECTION_OUTPUT_NAMES",
    "CONNECTION_POWER",
    "DEFERRABLE_LOAD_OUTPUT_NAMES",
    "ELEMENTS",
    "MODEL_ELEMENT_TYPE_BATTERY",
    "MODEL_ELEMENT_TYPE_BUFFER",
    "MODEL_ELEMENT_TYPE_CONNECTION",
    "MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD",
    "MODEL_ELEMENT_TYPE_NODE",
    "MODEL_ELEMENT_TYPE_POLICY_PRICING",
    "Battery",
    "BatteryConstraintName",
    "BatteryElementConfig",
    "BatteryOutputName",
    "Buffer",
    "BufferElementConfig",
    "BufferOutputName",
    "Connection",
    "ConnectionElementConfig",
    "ConnectionElementTypeName",
    "ConnectionOutputName",
    "DeferrableLoad",
    "DeferrableLoadConstraintName",
    "DeferrableLoadElementConfig",
    "DeferrableLoadOutputName",
    "EfficiencySegment",
    "ElementSpec",
    "ModelElementConfig",
    "ModelElementType",
    "NetworkElementConfig",
    "Node",
    "NodeElementConfig",
    "NodeOutputName",
    "PassthroughSegment",
    "PolicyPricing",
    "PolicyPricingElementConfig",
    "PolicyPricingTerm",
    "PowerLimitSegment",
    "PricingSegment",
    "Segment",
    "SegmentSpec",
    "SegmentType",
    "SourceElementConfig",
    "config_arguments",
    "is_network_element_config",
    "is_source_element_config",
]
