"""Thermal mass element schema definitions."""

from typing import Annotated, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import ConstantValue, EntityValue, NoneValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.field_hints import FieldHint, SectionHints
from custom_components.haeo.core.schema.sections import CommonConfig, CommonData

ELEMENT_TYPE = ElementType.THERMAL_MASS

SECTION_STORAGE: Final = "storage"
SECTION_COMFORT: Final = "comfort"
SECTION_SURROUNDINGS: Final = "surroundings"

CONF_HEAT_CAPACITY: Final = "heat_capacity"
CONF_TEMPERATURE: Final = "temperature"
CONF_LOWEST_TEMPERATURE: Final = "lowest_temperature"
CONF_HIGHEST_TEMPERATURE: Final = "highest_temperature"

CONF_MIN_TEMPERATURE: Final = "min_temperature"
CONF_MAX_TEMPERATURE: Final = "max_temperature"
CONF_COMFORT_COST: Final = "comfort_cost"

CONF_AMBIENT_TEMPERATURE: Final = "ambient_temperature"
CONF_HEAT_LOSS: Final = "heat_loss"


class StorageConfig(TypedDict):
    """Heat capacity, current temperature, and the temperatures heating and cooling may reach."""

    heat_capacity: EntityValue | ConstantValue
    temperature: EntityValue | ConstantValue
    lowest_temperature: NotRequired[EntityValue | ConstantValue | NoneValue]
    highest_temperature: NotRequired[EntityValue | ConstantValue | NoneValue]


class StorageData(TypedDict):
    """Loaded heat capacity, temperature, and temperature limits."""

    heat_capacity: float
    temperature: float
    lowest_temperature: NotRequired[float]
    highest_temperature: NotRequired[float]


class ComfortConfig(TypedDict):
    """The temperature band to keep, and the cost of leaving it."""

    min_temperature: NotRequired[EntityValue | ConstantValue | NoneValue]
    max_temperature: NotRequired[EntityValue | ConstantValue | NoneValue]
    comfort_cost: EntityValue | ConstantValue


class ComfortData(TypedDict):
    """Loaded temperature band and cost."""

    min_temperature: NotRequired[NDArray[np.float64]]
    max_temperature: NotRequired[NDArray[np.float64]]
    comfort_cost: NDArray[np.float64] | float


class SurroundingsConfig(TypedDict):
    """The temperature around the mass, and how fast heat passes to it."""

    ambient_temperature: EntityValue | ConstantValue
    heat_loss: EntityValue | ConstantValue


class SurroundingsData(TypedDict):
    """Loaded surroundings temperature and heat loss."""

    ambient_temperature: NDArray[np.float64] | float
    heat_loss: float


class ThermalMassConfigSchema(CommonConfig):
    """Thermal mass element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.THERMAL_MASS]
    storage: Annotated[
        StorageConfig,
        SectionHints(
            {
                CONF_HEAT_CAPACITY: FieldHint(output_type=OutputType.HEAT_CAPACITY),
                CONF_TEMPERATURE: FieldHint(output_type=OutputType.TEMPERATURE),
                CONF_LOWEST_TEMPERATURE: FieldHint(output_type=OutputType.TEMPERATURE),
                CONF_HIGHEST_TEMPERATURE: FieldHint(output_type=OutputType.TEMPERATURE),
            }
        ),
    ]
    comfort: Annotated[
        ComfortConfig,
        SectionHints(
            {
                CONF_MIN_TEMPERATURE: FieldHint(output_type=OutputType.TEMPERATURE, time_series=True, boundaries=True),
                CONF_MAX_TEMPERATURE: FieldHint(output_type=OutputType.TEMPERATURE, time_series=True, boundaries=True),
                CONF_COMFORT_COST: FieldHint(
                    output_type=OutputType.PRICE_RATE,
                    direction="-",
                    time_series=True,
                    min_value=0.0,
                    default_mode="value",
                    default_value=1.0,
                ),
            }
        ),
    ]
    surroundings: Annotated[
        SurroundingsConfig,
        SectionHints(
            {
                CONF_AMBIENT_TEMPERATURE: FieldHint(output_type=OutputType.TEMPERATURE, time_series=True),
                CONF_HEAT_LOSS: FieldHint(output_type=OutputType.CONDUCTANCE),
            }
        ),
    ]


class ThermalMassConfigData(CommonData):
    """Thermal mass element configuration with loaded values."""

    element_type: Literal[ElementType.THERMAL_MASS]
    storage: StorageData
    comfort: ComfortData
    surroundings: SurroundingsData


__all__ = [
    "CONF_AMBIENT_TEMPERATURE",
    "CONF_COMFORT_COST",
    "CONF_HEAT_CAPACITY",
    "CONF_HEAT_LOSS",
    "CONF_HIGHEST_TEMPERATURE",
    "CONF_LOWEST_TEMPERATURE",
    "CONF_MAX_TEMPERATURE",
    "CONF_MIN_TEMPERATURE",
    "CONF_TEMPERATURE",
    "ELEMENT_TYPE",
    "SECTION_COMFORT",
    "SECTION_STORAGE",
    "SECTION_SURROUNDINGS",
    "ComfortConfig",
    "ComfortData",
    "StorageConfig",
    "StorageData",
    "SurroundingsConfig",
    "SurroundingsData",
    "ThermalMassConfigData",
    "ThermalMassConfigSchema",
]
