"""Battery section element schema definitions.

This is an advanced element that provides direct access to the model layer Battery element.
Unlike the standard Battery element which creates multiple sections and an internal node,
this element creates a single battery section that must be connected manually via Connection.
"""

from typing import Any, Final, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.sections import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    SECTION_BASIC,
    SECTION_STORAGE,
    BasicNameConfig,
    BasicNameData,
)

ELEMENT_TYPE: Final = "battery_section"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset()


class BatterySectionStorageConfig(TypedDict):
    """Storage configuration for battery section elements."""

    capacity: str | float
    initial_charge: str | float


class BatterySectionStorageData(TypedDict):
    """Loaded storage values for battery section elements."""

    capacity: NDArray[np.floating[Any]] | float
    initial_charge: NDArray[np.floating[Any]] | float


class BatterySectionConfigSchema(TypedDict):
    """Battery section element configuration as stored in Home Assistant."""

    element_type: Literal["battery_section"]
    basic: BasicNameConfig
    storage: BatterySectionStorageConfig


class BatterySectionConfigData(TypedDict):
    """Battery section element configuration with loaded values."""

    element_type: Literal["battery_section"]
    basic: BasicNameData
    storage: BatterySectionStorageData


__all__ = [
    "CONF_CAPACITY",
    "CONF_INITIAL_CHARGE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_BASIC",
    "SECTION_STORAGE",
    "BatterySectionConfigData",
    "BatterySectionConfigSchema",
]
