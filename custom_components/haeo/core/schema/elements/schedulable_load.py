"""Schedulable load element schema definitions."""

from typing import Annotated, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import IntegerMode
from custom_components.haeo.core.schema import ConstantValue, EntityValue, NoneValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.field_hints import FieldHint, MeterFieldHint, SectionHints, calendar_input
from custom_components.haeo.core.schema.sections import ConnectedCommonConfig, ConnectedCommonData

ELEMENT_TYPE = ElementType.SCHEDULABLE_LOAD

# Section names
SECTION_SCHEDULE: Final = "schedule"
SECTION_PROFILE: Final = "profile"
SECTION_PRICING: Final = "pricing"
SECTION_ADVANCED: Final = "advanced"

# Schedule section field names
CONF_WINDOW_CALENDAR: Final = "window_calendar"
CONF_RUNNING: Final = "running"
CONF_ENERGY_METER: Final = "energy_meter"

# Inputs the window calendar feeds
CONF_IN_WINDOW: Final = "in_window"
CONF_WINDOW_START: Final = "window_start"

# Profile section field names
CONF_POWER: Final = "power"
CONF_DURATION: Final = "duration"

# Pricing section field names
CONF_DEFICIT_PRICE: Final = "deficit_price"

# Advanced section field names
CONF_INTEGER_MODE: Final = "integer_mode"
DEFAULT_INTEGER_MODE: Final[IntegerMode] = "first"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_RUNNING, CONF_ENERGY_METER})


# --- Schedule section ---


class ScheduleConfig(TypedDict):
    """Run window schedule configuration.

    The calendar drives the windows the load must run inside. The optional
    running sensor reports whether the load is running now, and the optional
    energy meter is a running total of the energy the load has used. How much
    the meter rose since the open window started tells how far through its
    run the load is, so a run already in progress is finished rather than
    planned again, and a window whose run is done takes no further run.
    """

    window_calendar: EntityValue
    running: NotRequired[EntityValue | NoneValue]
    energy_meter: NotRequired[EntityValue | NoneValue]


class ScheduleData(TypedDict):
    """Loaded run window schedule, with the inputs the window calendar feeds.

    The energy meter loads as the energy it counted since the open window began.
    """

    in_window: NDArray[np.float64]
    window_start: NDArray[np.float64]
    running: NotRequired[float]
    energy_meter: NotRequired[float]


# --- Profile section ---


class ProfileConfig(TypedDict):
    """Run profile configuration: the power drawn for the length of one run."""

    power: EntityValue | ConstantValue
    duration: EntityValue | ConstantValue


class ProfileData(TypedDict):
    """Loaded run profile values."""

    power: float
    duration: float


# --- Pricing section ---


class PricingConfig(TypedDict):
    """Missed run pricing configuration."""

    deficit_price: EntityValue | ConstantValue


class PricingData(TypedDict):
    """Loaded pricing values, one per horizon boundary."""

    deficit_price: NDArray[np.float64]


# --- Advanced section ---


class AdvancedConfig(TypedDict, total=False):
    """Solver options for the run start decision."""

    integer_mode: IntegerMode


# --- Main element schemas ---


class SchedulableLoadConfigSchema(ConnectedCommonConfig):
    """Schedulable load element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.SCHEDULABLE_LOAD]
    schedule: Annotated[
        ScheduleConfig,
        SectionHints(
            {
                CONF_WINDOW_CALENDAR: FieldHint(
                    output_type=OutputType.AVAILABILITY,
                    outputs={
                        CONF_IN_WINDOW: calendar_input(OutputType.AVAILABILITY, "window_active"),
                        CONF_WINDOW_START: calendar_input(OutputType.AVAILABILITY, "window_starts"),
                    },
                ),
                CONF_RUNNING: FieldHint(
                    output_type=OutputType.AVAILABILITY,
                    time_series=False,
                ),
                CONF_ENERGY_METER: FieldHint(
                    output_type=OutputType.ENERGY,
                    time_series=False,
                    meter=MeterFieldHint(since=CONF_WINDOW_CALENDAR),
                ),
            }
        ),
    ]
    profile: Annotated[
        ProfileConfig,
        SectionHints(
            {
                CONF_POWER: FieldHint(
                    output_type=OutputType.POWER,
                    direction="-",
                    time_series=False,
                ),
                CONF_DURATION: FieldHint(
                    output_type=OutputType.DURATION,
                    time_series=False,
                    min_value=0.0,
                    step=0.05,
                ),
            }
        ),
    ]
    pricing: Annotated[
        PricingConfig,
        SectionHints(
            {
                CONF_DEFICIT_PRICE: FieldHint(
                    output_type=OutputType.PRICE,
                    time_series=True,
                    boundaries=True,
                    min_value=0.0,
                    default_mode="value",
                    default_value=10.0,
                ),
            }
        ),
    ]
    advanced: NotRequired[AdvancedConfig]


class SchedulableLoadConfigData(ConnectedCommonData):
    """Schedulable load element configuration with loaded values."""

    element_type: Literal[ElementType.SCHEDULABLE_LOAD]
    schedule: ScheduleData
    profile: ProfileData
    pricing: PricingData
    advanced: NotRequired[AdvancedConfig]


__all__ = [
    "CONF_DEFICIT_PRICE",
    "CONF_DURATION",
    "CONF_ENERGY_METER",
    "CONF_INTEGER_MODE",
    "CONF_IN_WINDOW",
    "CONF_POWER",
    "CONF_RUNNING",
    "CONF_WINDOW_CALENDAR",
    "CONF_WINDOW_START",
    "DEFAULT_INTEGER_MODE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_ADVANCED",
    "SECTION_PRICING",
    "SECTION_PROFILE",
    "SECTION_SCHEDULE",
    "AdvancedConfig",
    "PricingConfig",
    "PricingData",
    "ProfileConfig",
    "ProfileData",
    "SchedulableLoadConfigData",
    "SchedulableLoadConfigSchema",
    "ScheduleConfig",
    "ScheduleData",
]
