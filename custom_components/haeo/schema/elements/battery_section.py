"""Battery section element schema definitions.

This is an advanced element that provides direct access to the model layer Battery element.
Unlike the standard Battery element which creates multiple sections and an internal node,
this element creates a single battery section that must be connected manually via Connection.
"""

from typing import Any, Final, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.schema import ConstantValue, EntityValue
from custom_components.haeo.sections import SECTION_COMMON, CommonConfig, CommonData

ELEMENT_TYPE: Final = "battery_section"

SECTION_STORAGE: Final = "storage"

CONF_CAPACITY: Final = "capacity"
CONF_INITIAL_CHARGE: Final = "initial_charge"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset()


class StorageChargeConfig(TypedDict):
    """Storage config with required initial charge."""

    capacity: EntityValue | ConstantValue
    initial_charge: EntityValue | ConstantValue


class StorageChargeData(TypedDict):
    """Loaded storage values with required initial charge."""

    capacity: NDArray[np.floating[Any]]
    initial_charge: NDArray[np.floating[Any]]


class BatterySectionConfigSchema(TypedDict):
    """Battery section element configuration as stored in Home Assistant."""

    element_type: Literal["battery_section"]
    common: CommonConfig
    storage: StorageChargeConfig


class BatterySectionConfigData(TypedDict):
    """Battery section element configuration with loaded values."""

    element_type: Literal["battery_section"]
    common: CommonData
    storage: StorageChargeData


__all__ = [
    "CONF_CAPACITY",
    "CONF_INITIAL_CHARGE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_COMMON",
    "SECTION_STORAGE",
    "BatterySectionConfigData",
    "BatterySectionConfigSchema",
    "StorageChargeConfig",
    "StorageChargeData",
]


