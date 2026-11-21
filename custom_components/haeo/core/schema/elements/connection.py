"""Connection element schema definitions.

A connection carries power from its source to its target through an ordered
list of segments. Each segment applies one thing to the power passing through
it, in the order listed: a limit, a price, or an efficiency. A connection with
no segments passes power through unchanged.
"""

from typing import Annotated, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import ConnectionTarget, ConstantValue, EntityValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.field_hints import FieldHint, ListFieldHints
from custom_components.haeo.core.schema.sections import CommonConfig, CommonData

ELEMENT_TYPE = ElementType.CONNECTION

SECTION_ENDPOINTS: Final = "endpoints"

CONF_SOURCE: Final = "source"
CONF_TARGET: Final = "target"
CONF_SEGMENTS: Final = "segments"
CONF_SEGMENT_TYPE: Final = "segment_type"

CONF_MAX_POWER: Final = "max_power"
CONF_PRICE: Final = "price"
CONF_EFFICIENCY: Final = "efficiency"

type SegmentType = Literal["power_limit", "pricing", "efficiency"]

# The one input each kind of segment takes, by segment type
SEGMENT_FIELDS: Final[dict[SegmentType, str]] = {
    "power_limit": CONF_MAX_POWER,
    "pricing": CONF_PRICE,
    "efficiency": CONF_EFFICIENCY,
}


class EndpointsConfig(TypedDict):
    """Endpoint configuration for source/target pairs."""

    source: ConnectionTarget
    target: ConnectionTarget


class EndpointsData(TypedDict):
    """Loaded endpoint values."""

    source: ConnectionTarget
    target: ConnectionTarget


class PowerLimitSegmentConfig(TypedDict):
    """A segment limiting the power passing through it."""

    segment_type: Literal["power_limit"]
    max_power: EntityValue | ConstantValue


class PricingSegmentConfig(TypedDict):
    """A segment charging a price on the power passing through it."""

    segment_type: Literal["pricing"]
    price: EntityValue | ConstantValue


class EfficiencySegmentConfig(TypedDict):
    """A segment losing a share of the power passing through it."""

    segment_type: Literal["efficiency"]
    efficiency: EntityValue | ConstantValue


type SegmentConfig = PowerLimitSegmentConfig | PricingSegmentConfig | EfficiencySegmentConfig


class PowerLimitSegmentData(TypedDict):
    """A limit segment with its input loaded."""

    segment_type: Literal["power_limit"]
    max_power: NotRequired[NDArray[np.float64] | float]


class PricingSegmentData(TypedDict):
    """A price segment with its input loaded."""

    segment_type: Literal["pricing"]
    price: NotRequired[NDArray[np.float64] | float]


class EfficiencySegmentData(TypedDict):
    """An efficiency segment with its input loaded."""

    segment_type: Literal["efficiency"]
    efficiency: NotRequired[NDArray[np.float64] | float]


type SegmentData = PowerLimitSegmentData | PricingSegmentData | EfficiencySegmentData


class ConnectionConfigSchema(CommonConfig):
    """Connection element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.CONNECTION]
    endpoints: EndpointsConfig
    segments: Annotated[
        list[SegmentConfig],
        ListFieldHints(
            fields={
                CONF_MAX_POWER: FieldHint(output_type=OutputType.POWER_LIMIT, time_series=True),
                CONF_PRICE: FieldHint(output_type=OutputType.PRICE, direction="-", time_series=True),
                CONF_EFFICIENCY: FieldHint(output_type=OutputType.EFFICIENCY, time_series=True),
            },
            kind_key=CONF_SEGMENT_TYPE,
            kind_fields={kind: (field,) for kind, field in SEGMENT_FIELDS.items()},
        ),
    ]


class ConnectionConfigData(CommonData):
    """Connection element configuration with loaded values."""

    element_type: Literal[ElementType.CONNECTION]
    endpoints: EndpointsData
    segments: list[SegmentData]


__all__ = [
    "CONF_EFFICIENCY",
    "CONF_MAX_POWER",
    "CONF_PRICE",
    "CONF_SEGMENTS",
    "CONF_SEGMENT_TYPE",
    "CONF_SOURCE",
    "CONF_TARGET",
    "ELEMENT_TYPE",
    "SECTION_ENDPOINTS",
    "SEGMENT_FIELDS",
    "ConnectionConfigData",
    "ConnectionConfigSchema",
    "EfficiencySegmentConfig",
    "EfficiencySegmentData",
    "EndpointsConfig",
    "EndpointsData",
    "PowerLimitSegmentConfig",
    "PowerLimitSegmentData",
    "PricingSegmentConfig",
    "PricingSegmentData",
    "SegmentConfig",
    "SegmentData",
    "SegmentType",
]
