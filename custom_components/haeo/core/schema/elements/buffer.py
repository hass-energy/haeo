"""Buffer element schema definitions.

A buffer keeps energy (a reserve) or empty space (headroom) in a group of
batteries, for a group of loads and generation over a window of time, measured
from a level of the batteries' charge.
"""

from typing import Annotated, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.constant_value import ConstantValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.entity_value import EntityValue
from custom_components.haeo.core.schema.field_hints import FieldHint, SectionHints
from custom_components.haeo.core.schema.none_value import NoneValue

ELEMENT_TYPE = ElementType.BUFFER

SECTION_PARTICIPANTS: Final = "participants"
SECTION_REQUIREMENT: Final = "requirement"
SECTION_PRICING: Final = "pricing"

CONF_KIND: Final = "kind"
CONF_LOADS: Final = "loads"
CONF_GENERATION: Final = "generation"
CONF_STORAGE: Final = "storage"
CONF_WINDOW: Final = "window"
CONF_LEVEL: Final = "level"
CONF_SHORTFALL_COST: Final = "shortfall_cost"

# A reserve keeps energy in the batteries and headroom keeps empty space
KIND_RESERVE: Final = "reserve"
KIND_HEADROOM: Final = "headroom"
type BufferKind = Literal["reserve", "headroom"]
BUFFER_KINDS: Final[tuple[BufferKind, ...]] = (KIND_RESERVE, KIND_HEADROOM)

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_LEVEL})


class ParticipantsConfig(TypedDict):
    """Elements the buffer covers and the batteries that hold it."""

    loads: NotRequired[list[str]]
    generation: NotRequired[list[str]]
    storage: list[str]


class RequirementConfig(TypedDict):
    """How far ahead the buffer looks and the charge level it is measured from."""

    window: EntityValue | ConstantValue
    level: NotRequired[EntityValue | ConstantValue | NoneValue]


class RequirementData(TypedDict):
    """Loaded requirement values."""

    window: float
    level: NotRequired[NDArray[np.float64] | float]


class BufferPricingConfig(TypedDict):
    """Cost of falling short of the buffer."""

    shortfall_cost: EntityValue | ConstantValue


class BufferPricingData(TypedDict):
    """Loaded buffer pricing values."""

    shortfall_cost: NDArray[np.float64] | float


class BufferConfigSchema(TypedDict):
    """Buffer element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.BUFFER]
    name: str
    kind: BufferKind
    participants: ParticipantsConfig
    requirement: Annotated[
        RequirementConfig,
        SectionHints(
            {
                CONF_WINDOW: FieldHint(
                    output_type=OutputType.DURATION,
                    default_mode="value",
                    default_value=12.0,
                ),
                CONF_LEVEL: FieldHint(
                    output_type=OutputType.STATE_OF_CHARGE,
                    time_series=True,
                    boundaries=True,
                ),
            }
        ),
    ]
    pricing: Annotated[
        BufferPricingConfig,
        SectionHints(
            {
                CONF_SHORTFALL_COST: FieldHint(
                    output_type=OutputType.PRICE_RATE,
                    direction="-",
                    time_series=True,
                    min_value=0.0,
                    default_mode="value",
                    default_value=0.05,
                ),
            }
        ),
    ]


class BufferConfigData(TypedDict):
    """Buffer element configuration with loaded values."""

    element_type: Literal[ElementType.BUFFER]
    name: str
    kind: BufferKind
    participants: ParticipantsConfig
    requirement: RequirementData
    pricing: BufferPricingData


__all__ = [
    "BUFFER_KINDS",
    "CONF_GENERATION",
    "CONF_KIND",
    "CONF_LEVEL",
    "CONF_LOADS",
    "CONF_SHORTFALL_COST",
    "CONF_STORAGE",
    "CONF_WINDOW",
    "ELEMENT_TYPE",
    "KIND_HEADROOM",
    "KIND_RESERVE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_PARTICIPANTS",
    "SECTION_PRICING",
    "SECTION_REQUIREMENT",
    "BufferConfigData",
    "BufferConfigSchema",
    "BufferKind",
    "BufferPricingConfig",
    "BufferPricingData",
    "ParticipantsConfig",
    "RequirementConfig",
    "RequirementData",
]
