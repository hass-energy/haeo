"""Deferrable load element schema definitions."""

from typing import Annotated, Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.data.loader.calendar_resolver import CalendarBoundaryData
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import CalendarValue, ConstantValue, EntityValue, NoneValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.field_hints import CalendarFieldHint, FieldHint, SectionHints
from custom_components.haeo.core.schema.sections import ConnectedCommonConfig, ConnectedCommonData

ELEMENT_TYPE = ElementType.DEFERRABLE_LOAD

# Section names
SECTION_SCHEDULE: Final = "schedule"
SECTION_POWER: Final = "power"
SECTION_PRICING: Final = "pricing"

# Schedule section field names
CONF_WINDOW_CALENDAR: Final = "window_calendar"
CONF_ENERGY_DELIVERED: Final = "energy_delivered"

# Power section field names
CONF_MAX_POWER: Final = "max_power"

# Pricing section field names
CONF_DEFICIT_PRICE: Final = "deficit_price"
CONF_OVERAGE_PRICE: Final = "overage_price"

# Default deficit price ($/kWh) pre-filled in the flow: high enough that the
# load runs whenever physically possible, finite so it can never make the
# optimization infeasible.
DEFAULT_DEFICIT_PRICE: Final = 10.0

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        CONF_ENERGY_DELIVERED,
        CONF_MAX_POWER,
        CONF_OVERAGE_PRICE,
    }
)


# --- Schedule section ---


class ScheduleConfig(TypedDict):
    """Run window schedule configuration.

    The calendar drives the run windows and their energy requirements; the
    optional delivered energy sensor reports how much the currently open
    window has already received, so re-optimizing mid-window does not demand
    that energy again.
    """

    window_calendar: CalendarValue
    energy_delivered: NotRequired[EntityValue | NoneValue]


class ScheduleData(TypedDict):
    """Loaded run window schedule."""

    window_calendar: CalendarBoundaryData
    energy_delivered: NotRequired[float]


# --- Power section ---


class PowerConfig(TypedDict, total=False):
    """Power limit configuration."""

    max_power: EntityValue | ConstantValue | NoneValue


class PowerData(TypedDict, total=False):
    """Loaded power limit values."""

    max_power: NDArray[np.floating[Any]] | float


# --- Pricing section ---


class PricingConfig(TypedDict):
    """Shortfall and overage pricing configuration."""

    deficit_price: EntityValue | ConstantValue
    overage_price: NotRequired[EntityValue | ConstantValue | NoneValue]


class PricingData(TypedDict):
    """Loaded pricing values."""

    deficit_price: NDArray[np.floating[Any]] | float
    overage_price: NotRequired[NDArray[np.floating[Any]] | float]


# --- Main element schemas ---


class DeferrableLoadConfigSchema(ConnectedCommonConfig):
    """Deferrable load element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.DEFERRABLE_LOAD]
    schedule: Annotated[
        ScheduleConfig,
        SectionHints(
            {
                CONF_WINDOW_CALENDAR: FieldHint(
                    output_type=OutputType.ENERGY,
                    time_series=True,
                    boundaries=True,
                    calendar=CalendarFieldHint(parser="number"),
                ),
                CONF_ENERGY_DELIVERED: FieldHint(
                    output_type=OutputType.ENERGY,
                    time_series=False,
                    min_value=0.0,
                ),
            }
        ),
    ]
    power: NotRequired[
        Annotated[
            PowerConfig,
            SectionHints(
                {
                    CONF_MAX_POWER: FieldHint(
                        output_type=OutputType.POWER_LIMIT,
                        direction="-",
                        time_series=True,
                    ),
                }
            ),
        ]
    ]
    pricing: Annotated[
        PricingConfig,
        SectionHints(
            {
                CONF_DEFICIT_PRICE: FieldHint(
                    output_type=OutputType.PRICE,
                    time_series=True,
                    min_value=0.0,
                    default_mode="value",
                    default_value=DEFAULT_DEFICIT_PRICE,
                ),
                CONF_OVERAGE_PRICE: FieldHint(
                    output_type=OutputType.PRICE,
                    time_series=True,
                    min_value=0.0,
                ),
            }
        ),
    ]


class DeferrableLoadConfigData(ConnectedCommonData):
    """Deferrable load element configuration with loaded values."""

    element_type: Literal[ElementType.DEFERRABLE_LOAD]
    schedule: ScheduleData
    power: NotRequired[PowerData]
    pricing: PricingData


__all__ = [
    "CONF_DEFICIT_PRICE",
    "CONF_ENERGY_DELIVERED",
    "CONF_MAX_POWER",
    "CONF_OVERAGE_PRICE",
    "CONF_WINDOW_CALENDAR",
    "DEFAULT_DEFICIT_PRICE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_POWER",
    "SECTION_PRICING",
    "SECTION_SCHEDULE",
    "DeferrableLoadConfigData",
    "DeferrableLoadConfigSchema",
    "PowerConfig",
    "PowerData",
    "PricingConfig",
    "PricingData",
    "ScheduleConfig",
    "ScheduleData",
]
