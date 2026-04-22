"""Battery element schema definitions."""

from typing import Annotated, Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import ConstantValue, EntityValue, NoneValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.field_hints import FieldHint, ListFieldHints, SectionHints
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    ConnectedCommonConfig,
    ConnectedCommonData,
    EfficiencyConfig,
    EfficiencyData,
    PowerLimitsConfig,
    PowerLimitsData,
)

ELEMENT_TYPE = ElementType.BATTERY

SECTION_STORAGE: Final = "storage"

CONF_CAPACITY: Final = "capacity"
CONF_INITIAL_CHARGE_PERCENTAGE: Final = "initial_charge_percentage"

CONF_SALVAGE_VALUE: Final = "salvage_value"

CONF_INVENTORY_COSTS: Final = "inventory_costs"
CONF_COST_NAME: Final = "name"
CONF_DIRECTION: Final = "direction"
CONF_THRESHOLD: Final = "threshold"
CONF_COST: Final = "cost"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        CONF_MAX_POWER_SOURCE_TARGET,
        CONF_MAX_POWER_TARGET_SOURCE,
        CONF_EFFICIENCY_SOURCE_TARGET,
        CONF_EFFICIENCY_TARGET_SOURCE,
    }
)


class StorageSocConfig(TypedDict):
    """Storage config with required SOC percentage."""

    capacity: EntityValue | ConstantValue
    initial_charge_percentage: EntityValue | ConstantValue


class StorageSocData(TypedDict):
    """Loaded storage values with required SOC percentage."""

    capacity: NDArray[np.floating[Any]]
    initial_charge_percentage: float


class BatteryPricingConfig(TypedDict, total=False):
    """Battery pricing configuration values."""

    salvage_value: NotRequired[EntityValue | ConstantValue | NoneValue]


class BatteryPricingData(TypedDict, total=False):
    """Loaded battery pricing values."""

    salvage_value: NotRequired[float]


class InventoryCostConfig(TypedDict):
    """A single inventory cost rule as stored in Home Assistant config."""

    name: str
    direction: Literal["above", "below"]
    threshold: EntityValue | ConstantValue
    cost: EntityValue | ConstantValue


class InventoryCostData(TypedDict):
    """A single inventory cost rule with loaded values."""

    name: str
    direction: Literal["above", "below"]
    threshold: NDArray[np.floating[Any]] | float
    cost: NDArray[np.floating[Any]] | float


class BatteryConfigSchema(ConnectedCommonConfig):
    """Battery element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.BATTERY]
    storage: Annotated[
        StorageSocConfig,
        SectionHints(
            {
                CONF_CAPACITY: FieldHint(
                    output_type=OutputType.ENERGY,
                    time_series=True,
                    boundaries=True,
                ),
                CONF_INITIAL_CHARGE_PERCENTAGE: FieldHint(
                    output_type=OutputType.STATE_OF_CHARGE,
                    time_series=False,
                    step=0.1,
                ),
            }
        ),
    ]
    power_limits: Annotated[
        PowerLimitsConfig,
        SectionHints(
            {
                CONF_MAX_POWER_TARGET_SOURCE: FieldHint(
                    output_type=OutputType.POWER,
                    direction="+",
                    time_series=True,
                    step=0.1,
                    default_mode="entity",
                ),
                CONF_MAX_POWER_SOURCE_TARGET: FieldHint(
                    output_type=OutputType.POWER,
                    direction="-",
                    time_series=True,
                    step=0.1,
                    default_mode="entity",
                ),
            }
        ),
    ]
    pricing: Annotated[
        BatteryPricingConfig,
        SectionHints(
            {
                CONF_SALVAGE_VALUE: FieldHint(
                    output_type=OutputType.PRICE,
                    time_series=False,
                    default_mode="value",
                    default_value=0.0,
                ),
            }
        ),
    ]
    efficiency: Annotated[
        EfficiencyConfig,
        SectionHints(
            {
                CONF_EFFICIENCY_SOURCE_TARGET: FieldHint(
                    output_type=OutputType.EFFICIENCY,
                    time_series=True,
                    default_mode="value",
                    default_value=95.0,
                ),
                CONF_EFFICIENCY_TARGET_SOURCE: FieldHint(
                    output_type=OutputType.EFFICIENCY,
                    time_series=True,
                    default_mode="value",
                    default_value=95.0,
                ),
            }
        ),
    ]
    inventory_costs: NotRequired[
        Annotated[
            list[InventoryCostConfig],
            ListFieldHints(
                fields={
                    CONF_THRESHOLD: FieldHint(
                        output_type=OutputType.ENERGY,
                        time_series=True,
                        boundaries=True,
                    ),
                    CONF_COST: FieldHint(
                        output_type=OutputType.PRICE,
                        time_series=True,
                    ),
                },
            ),
        ]
    ]


class BatteryConfigData(ConnectedCommonData):
    """Battery element configuration with loaded values."""

    element_type: Literal[ElementType.BATTERY]
    storage: StorageSocData
    power_limits: PowerLimitsData
    pricing: BatteryPricingData
    efficiency: EfficiencyData
    inventory_costs: NotRequired[list[InventoryCostData]]


__all__ = [
    "CONF_CAPACITY",
    "CONF_CONNECTION",
    "CONF_COST",
    "CONF_COST_NAME",
    "CONF_DIRECTION",
    "CONF_EFFICIENCY_SOURCE_TARGET",
    "CONF_EFFICIENCY_TARGET_SOURCE",
    "CONF_INITIAL_CHARGE_PERCENTAGE",
    "CONF_INVENTORY_COSTS",
    "CONF_MAX_POWER_SOURCE_TARGET",
    "CONF_MAX_POWER_TARGET_SOURCE",
    "CONF_SALVAGE_VALUE",
    "CONF_THRESHOLD",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_EFFICIENCY",
    "SECTION_POWER_LIMITS",
    "SECTION_PRICING",
    "SECTION_STORAGE",
    "BatteryConfigData",
    "BatteryConfigSchema",
    "BatteryPricingConfig",
    "BatteryPricingData",
    "InventoryCostConfig",
    "InventoryCostData",
    "StorageSocConfig",
    "StorageSocData",
]
