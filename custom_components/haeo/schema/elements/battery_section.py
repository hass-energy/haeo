"""Battery section element schema definitions.

This is an advanced element that provides direct access to the model layer Battery element.
Unlike the standard Battery element which creates multiple sections and an internal node,
this element creates a single battery section that must be connected manually via Connection.
"""

from typing import Annotated, Any, Final, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.sections import SECTION_COMMON, CommonConfig, CommonData
from custom_components.haeo.schema import ConstantValue, EntityValue
from custom_components.haeo.schema.elements import ElementType
from custom_components.haeo.schema.field_hints import FieldHint, SectionHints

ELEMENT_TYPE = ElementType.BATTERY_SECTION

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

    element_type: Literal[ElementType.BATTERY_SECTION]
    common: CommonConfig
    storage: Annotated[
        StorageChargeConfig,
        SectionHints(
            {
                CONF_CAPACITY: FieldHint(
                    output_type=OutputType.ENERGY,
                    time_series=True,
                    boundaries=True,
                    min_value=0.1,
                ),
                CONF_INITIAL_CHARGE: FieldHint(
                    output_type=OutputType.ENERGY,
                    time_series=True,
                    boundaries=True,
                    min_value=0.0,
                ),
            }
        ),
    ]


class BatterySectionConfigData(TypedDict):
    """Battery section element configuration with loaded values."""

    element_type: Literal[ElementType.BATTERY_SECTION]
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
