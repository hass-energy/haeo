"""Battery section element schema definitions.

This is an advanced element that provides direct access to the model layer Battery element.
Unlike the standard Battery element which creates multiple sections and an internal node,
this element creates a single battery section that must be connected manually via Connection.
"""

from typing import Final, Literal, TypedDict

from custom_components.haeo.sections import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    SECTION_DETAILS,
    SECTION_STORAGE,
    DetailsConfig,
    DetailsData,
    StorageChargeConfig,
    StorageChargeData,
)

ELEMENT_TYPE: Final = "battery_section"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset()


class BatterySectionConfigSchema(TypedDict):
    """Battery section element configuration as stored in Home Assistant."""

    element_type: Literal["battery_section"]
    details: DetailsConfig
    storage: StorageChargeConfig


class BatterySectionConfigData(TypedDict):
    """Battery section element configuration with loaded values."""

    element_type: Literal["battery_section"]
    details: DetailsData
    storage: StorageChargeData


__all__ = [
    "CONF_CAPACITY",
    "CONF_INITIAL_CHARGE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_DETAILS",
    "SECTION_STORAGE",
    "BatterySectionConfigData",
    "BatterySectionConfigSchema",
]
