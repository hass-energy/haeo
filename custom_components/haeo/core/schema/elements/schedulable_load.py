"""Schedulable load element schema definitions."""

from typing import Annotated, Final, Literal, NotRequired, TypedDict

from custom_components.haeo.core.data.loader.calendar_resolver import CalendarBoundaryData
from custom_components.haeo.core.data.loader.source_history import OffPeriod
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import IntegerMode
from custom_components.haeo.core.schema import CalendarValue, ConstantValue, EntityValue, NoneValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.field_hints import CalendarFieldHint, FieldHint, SectionHints
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
# Loaded beside the running field: the periods the running sensor read off,
# from Home Assistant's history.
CONF_RUNNING_OFF_PERIODS: Final = "running_off_periods"

# Profile section field names
CONF_POWER: Final = "power"
CONF_DURATION: Final = "duration"

# Pricing section field names
CONF_DEFICIT_PRICE: Final = "deficit_price"

# Advanced section field names
CONF_INTEGER_MODE: Final = "integer_mode"
DEFAULT_INTEGER_MODE: Final[IntegerMode] = "first"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_RUNNING})


# --- Schedule section ---


class ScheduleConfig(TypedDict):
    """Run window schedule configuration.

    The calendar drives the windows the load must run inside; the optional
    running sensor reports whether the load is running now, so a run already
    in progress is finished rather than planned again.
    """

    window_calendar: CalendarValue
    running: NotRequired[EntityValue | NoneValue]


class ScheduleData(TypedDict):
    """Loaded run window schedule."""

    window_calendar: CalendarBoundaryData
    running: NotRequired[float]
    running_off_periods: NotRequired[list[OffPeriod]]


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
    """Loaded pricing values."""

    deficit_price: float


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
                    output_type=OutputType.STATUS,
                    time_series=True,
                    boundaries=True,
                    calendar=CalendarFieldHint(parser="presence"),
                ),
                CONF_RUNNING: FieldHint(
                    output_type=OutputType.AVAILABILITY,
                    time_series=False,
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
                    time_series=False,
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
    "CONF_INTEGER_MODE",
    "CONF_POWER",
    "CONF_RUNNING",
    "CONF_RUNNING_OFF_PERIODS",
    "CONF_WINDOW_CALENDAR",
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
