"""Buffer element schema definitions.

A buffer keeps energy (a reserve) or empty space (headroom) in a group of
batteries, for a group of loads and generation over a window of time, measured
from a level of the batteries' charge.

Loads and generation are power sensors. A sensor of one of the hub's own load
or generation elements stands for that element, which then takes part through
its planned flows.
"""

from collections.abc import Callable, Mapping
from typing import Annotated, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.constant_value import ConstantValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.entity_value import EntityValue, is_entity_value
from custom_components.haeo.core.schema.field_hints import ElementsData, FieldHint, SectionHints
from custom_components.haeo.core.schema.none_value import NoneValue

ELEMENT_TYPE = ElementType.BUFFER

SECTION_PARTICIPANTS: Final = "participants"
SECTION_REQUIREMENT: Final = "requirement"
SECTION_PRICING: Final = "pricing"

CONF_KIND: Final = "kind"
CONF_LOADS: Final = "loads"
CONF_GENERATION: Final = "generation"
CONF_STORAGE: Final = "storage"

# The roles an element can take in a buffer, named by the participant list
# that holds it
type BufferRole = Literal["loads", "generation", "storage"]
BUFFER_ROLES: Final[tuple[BufferRole, ...]] = (CONF_LOADS, CONF_GENERATION, CONF_STORAGE)
CONF_WINDOW: Final = "window"
CONF_LEVEL: Final = "level"
CONF_SHORTFALL_COST: Final = "shortfall_cost"

# A reserve keeps energy in the batteries and headroom keeps empty space
KIND_RESERVE: Final = "reserve"
KIND_HEADROOM: Final = "headroom"
type BufferKind = Literal["reserve", "headroom"]
BUFFER_KINDS: Final[tuple[BufferKind, ...]] = (KIND_RESERVE, KIND_HEADROOM)


class ParticipantsConfig(TypedDict):
    """Loads and generation the buffer covers and the batteries that hold it."""

    loads: NotRequired[EntityValue | ConstantValue | NoneValue]
    generation: NotRequired[EntityValue | ConstantValue | NoneValue]
    storage: list[str]


class ParticipantsData(TypedDict):
    """Loaded participants: the elements named and the power of the other sensors."""

    loads: NotRequired[ElementsData]
    generation: NotRequired[ElementsData]
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
    participants: Annotated[
        ParticipantsConfig,
        SectionHints(
            {
                CONF_LOADS: FieldHint(
                    output_type=OutputType.POWER,
                    direction="-",
                    time_series=True,
                    element_role=CONF_LOADS,
                ),
                CONF_GENERATION: FieldHint(
                    output_type=OutputType.POWER,
                    direction="+",
                    time_series=True,
                    element_role=CONF_GENERATION,
                ),
            }
        ),
    ]
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
    participants: ParticipantsData
    requirement: RequirementData
    pricing: BufferPricingData


def map_references(config: Mapping[str, object], resolve: Callable[[str], str]) -> dict[str, object]:
    """Return the buffer with each element it names replaced by what resolve returns for it.

    It names batteries in a list, and loads and generation in the ``elements``
    of their sensor fields. Sensors that stand for elements keep their entity
    IDs when an element is renamed, so they are left as they are. An element
    renamed to a name its list already holds is listed once.
    """
    participants = config[SECTION_PARTICIPANTS]
    if not isinstance(participants, Mapping):
        return dict(config)
    mapped: dict[str, object] = dict(participants)
    if isinstance(storage := participants.get(CONF_STORAGE), list):
        mapped[CONF_STORAGE] = list(dict.fromkeys(resolve(name) for name in storage))
    for role in (CONF_LOADS, CONF_GENERATION):
        value = participants.get(role)
        if is_entity_value(value) and "elements" in value:
            mapped[role] = {**value, "elements": list(dict.fromkeys(resolve(name) for name in value["elements"]))}
    return {**config, SECTION_PARTICIPANTS: mapped}


__all__ = [
    "BUFFER_KINDS",
    "BUFFER_ROLES",
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
    "SECTION_PARTICIPANTS",
    "SECTION_PRICING",
    "SECTION_REQUIREMENT",
    "BufferConfigData",
    "BufferConfigSchema",
    "BufferKind",
    "BufferPricingConfig",
    "BufferPricingData",
    "BufferRole",
    "ParticipantsConfig",
    "ParticipantsData",
    "RequirementConfig",
    "RequirementData",
    "map_references",
]
