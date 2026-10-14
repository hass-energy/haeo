"""Reserve element schema definitions.

A reserve keeps enough energy in a group of batteries to cover a group of
loads, less a group of generators, through a grid outage of a set length.

Headroom shares the same configuration, so its schema builds on the
``StorageRequirementConfig`` and ``StorageRequirementData`` defined here.
"""

from typing import Annotated, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.constant_value import ConstantValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.entity_value import EntityValue
from custom_components.haeo.core.schema.field_hints import FieldHint, SectionHints

ELEMENT_TYPE = ElementType.RESERVE

SECTION_PARTICIPANTS: Final = "participants"
SECTION_REQUIREMENT: Final = "requirement"
SECTION_PRICING: Final = "pricing"

CONF_LOADS: Final = "loads"
CONF_GENERATION: Final = "generation"
CONF_STORAGE: Final = "storage"
CONF_WINDOW: Final = "window"
CONF_MINIMUM: Final = "minimum"
CONF_SHORTFALL_COST: Final = "shortfall_cost"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset()


class ParticipantsConfig(TypedDict):
    """Elements the reserve covers and the batteries that hold it."""

    loads: NotRequired[list[str]]
    generation: NotRequired[list[str]]
    storage: list[str]


class RequirementConfig(TypedDict):
    """How long an outage the reserve covers and how much extra it holds."""

    window: ConstantValue
    minimum: EntityValue | ConstantValue


class RequirementData(TypedDict):
    """Loaded requirement values."""

    window: float
    minimum: NDArray[np.float64] | float


class ReservePricingConfig(TypedDict):
    """Cost of falling short of the reserve."""

    shortfall_cost: EntityValue | ConstantValue


class ReservePricingData(TypedDict):
    """Loaded reserve pricing values."""

    shortfall_cost: NDArray[np.float64] | float


class StorageRequirementConfig(TypedDict):
    """Configuration shared by reserves and headroom, as stored in Home Assistant."""

    name: str
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
                CONF_MINIMUM: FieldHint(
                    output_type=OutputType.ENERGY,
                    time_series=True,
                    boundaries=True,
                    min_value=0.0,
                    default_mode="value",
                    default_value=0.0,
                ),
            }
        ),
    ]
    pricing: Annotated[
        ReservePricingConfig,
        SectionHints(
            {
                CONF_SHORTFALL_COST: FieldHint(
                    output_type=OutputType.PRICE_RATE,
                    direction="-",
                    time_series=True,
                    default_mode="value",
                    default_value=0.05,
                ),
            }
        ),
    ]


class StorageRequirementData(TypedDict):
    """Configuration shared by reserves and headroom, with loaded values."""

    name: str
    participants: ParticipantsConfig
    requirement: RequirementData
    pricing: ReservePricingData


class ReserveConfigSchema(StorageRequirementConfig):
    """Reserve element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.RESERVE]


class ReserveConfigData(StorageRequirementData):
    """Reserve element configuration with loaded values."""

    element_type: Literal[ElementType.RESERVE]


__all__ = [
    "CONF_GENERATION",
    "CONF_LOADS",
    "CONF_MINIMUM",
    "CONF_SHORTFALL_COST",
    "CONF_STORAGE",
    "CONF_WINDOW",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_PARTICIPANTS",
    "SECTION_PRICING",
    "SECTION_REQUIREMENT",
    "ParticipantsConfig",
    "RequirementConfig",
    "RequirementData",
    "ReserveConfigData",
    "ReserveConfigSchema",
    "ReservePricingConfig",
    "ReservePricingData",
    "StorageRequirementConfig",
    "StorageRequirementData",
]
