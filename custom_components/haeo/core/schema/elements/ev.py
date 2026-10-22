"""EV element schema definitions."""

from typing import Annotated, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import ConstantValue, EntityValue, NoneValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.field_hints import FieldHint, MeterFieldHint, SectionHints, calendar_input
from custom_components.haeo.core.schema.sections import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    ConnectedCommonConfig,
    ConnectedCommonData,
    EfficiencyConfig,
    EfficiencyData,
)

ELEMENT_TYPE = ElementType.EV

# Section names
SECTION_VEHICLE: Final = "vehicle"
SECTION_CHARGING: Final = "charging"
SECTION_TRIP: Final = "trip"
SECTION_PUBLIC_CHARGING: Final = "public_charging"
SECTION_ADVANCED: Final = "advanced"

# Vehicle section field names
CONF_CAPACITY: Final = "capacity"
CONF_ENERGY_PER_DISTANCE: Final = "energy_per_distance"
CONF_CURRENT_SOC: Final = "current_soc"
CONF_MIN_CHARGE_PERCENTAGE: Final = "min_charge_percentage"

# Charging section field names
CONF_MAX_CHARGE_RATE: Final = "max_charge_rate"
CONF_MAX_DISCHARGE_RATE: Final = "max_discharge_rate"
CONF_CONNECTED: Final = "connected"

# Trip section field names
CONF_TRIP_CALENDAR: Final = "trip_calendar"
# Inputs the trip calendar feeds: the periods away, where trips start, and
# the distances of the trips starting and ending at each boundary.
CONF_AWAY: Final = "away"
CONF_TRIP_START: Final = "trip_start"
CONF_TRIP_OPENED: Final = "trip_opened"
CONF_TRIP_DUE: Final = "trip_due"
CONF_ODOMETER: Final = "odometer"

# Public charging section field names
CONF_PUBLIC_CHARGING_PRICE: Final = "public_charging_price"

# Advanced section field names
CONF_CHARGE_LIMIT_COST: Final = "charge_limit_cost"


# --- Vehicle section ---


class VehicleConfig(TypedDict):
    """Vehicle details configuration."""

    capacity: EntityValue | ConstantValue
    energy_per_distance: EntityValue | ConstantValue
    current_soc: EntityValue
    min_charge_percentage: NotRequired[EntityValue | ConstantValue | NoneValue]


class VehicleData(TypedDict):
    """Loaded vehicle details."""

    capacity: NDArray[np.float64]
    energy_per_distance: float
    current_soc: float
    min_charge_percentage: NotRequired[NDArray[np.float64]]


# --- Charging section ---


class ChargingConfig(TypedDict):
    """Charging configuration: the home charger's rates and whether the car is plugged in."""

    max_charge_rate: EntityValue | ConstantValue
    max_discharge_rate: NotRequired[EntityValue | ConstantValue | NoneValue]
    connected: EntityValue


class ChargingData(TypedDict):
    """Loaded charging values."""

    max_charge_rate: NDArray[np.float64] | float
    max_discharge_rate: NotRequired[NDArray[np.float64] | float]
    connected: bool


# --- Trip section ---


class TripConfig(TypedDict, total=False):
    """Trip configuration.

    The trip calendar drives when the car is away and how far each trip
    goes. The odometer reports how far the open trip has gone, so a car that
    is driving or back home is not planned as if it had not left.
    """

    trip_calendar: EntityValue | NoneValue
    odometer: EntityValue | NoneValue


class TripData(TypedDict, total=False):
    """Loaded trip values, with the inputs the trip calendar feeds.

    The odometer loads as the distance driven since the open trip began.
    """

    away: NDArray[np.float64]
    trip_start: NDArray[np.float64]
    trip_opened: NDArray[np.float64]
    trip_due: NDArray[np.float64]
    odometer: float


# --- Public charging section ---


class PublicChargingConfig(TypedDict, total=False):
    """Public charging pricing configuration."""

    public_charging_price: EntityValue | ConstantValue | NoneValue


class PublicChargingData(TypedDict, total=False):
    """Loaded public charging pricing values."""

    public_charging_price: NDArray[np.float64] | float


# --- Advanced section ---


class AdvancedConfig(TypedDict):
    """Advanced EV configuration values."""

    charge_limit_cost: EntityValue | ConstantValue


class AdvancedData(TypedDict):
    """Loaded advanced EV values."""

    charge_limit_cost: NDArray[np.float64] | float


# --- Main element schemas ---


class EvConfigSchema(ConnectedCommonConfig):
    """EV element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.EV]
    vehicle: Annotated[
        VehicleConfig,
        SectionHints(
            {
                CONF_CAPACITY: FieldHint(
                    output_type=OutputType.ENERGY,
                    time_series=True,
                    boundaries=True,
                ),
                CONF_ENERGY_PER_DISTANCE: FieldHint(
                    output_type=OutputType.ENERGY_PER_DISTANCE,
                    time_series=False,
                ),
                CONF_CURRENT_SOC: FieldHint(
                    output_type=OutputType.STATE_OF_CHARGE,
                    time_series=False,
                    step=0.1,
                ),
                CONF_MIN_CHARGE_PERCENTAGE: FieldHint(
                    output_type=OutputType.STATE_OF_CHARGE,
                    time_series=True,
                    boundaries=True,
                ),
            }
        ),
    ]
    charging: Annotated[
        ChargingConfig,
        SectionHints(
            {
                CONF_MAX_CHARGE_RATE: FieldHint(
                    output_type=OutputType.POWER,
                    direction="-",
                    time_series=True,
                    step=0.1,
                ),
                CONF_MAX_DISCHARGE_RATE: FieldHint(
                    output_type=OutputType.POWER,
                    direction="+",
                    time_series=True,
                    step=0.1,
                ),
                CONF_CONNECTED: FieldHint(
                    output_type=OutputType.STATUS,
                    time_series=False,
                ),
            }
        ),
    ]
    trip: NotRequired[
        Annotated[
            TripConfig,
            SectionHints(
                {
                    CONF_TRIP_CALENDAR: FieldHint(
                        output_type=OutputType.DISTANCE,
                        outputs={
                            CONF_AWAY: calendar_input(OutputType.AVAILABILITY, "window_active"),
                            CONF_TRIP_START: calendar_input(OutputType.AVAILABILITY, "window_starts"),
                            CONF_TRIP_OPENED: calendar_input(OutputType.DISTANCE, "event_opens"),
                            CONF_TRIP_DUE: calendar_input(OutputType.DISTANCE, "event_due"),
                        },
                    ),
                    CONF_ODOMETER: FieldHint(
                        output_type=OutputType.DISTANCE,
                        time_series=False,
                        meter=MeterFieldHint(since=CONF_TRIP_CALENDAR),
                    ),
                }
            ),
        ]
    ]
    public_charging: NotRequired[
        Annotated[
            PublicChargingConfig,
            SectionHints(
                {
                    CONF_PUBLIC_CHARGING_PRICE: FieldHint(
                        output_type=OutputType.PRICE,
                        time_series=True,
                        boundaries=True,
                        min_value=0.0,
                    ),
                }
            ),
        ]
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

    advanced: Annotated[
        AdvancedConfig,
        SectionHints(
            {
                CONF_CHARGE_LIMIT_COST: FieldHint(
                    output_type=OutputType.PRICE_RATE,
                    direction="-",
                    time_series=True,
                    min_value=0.0,
                    default_mode="value",
                    default_value=100.0,
                ),
            }
        ),
    ]


class EvConfigData(ConnectedCommonData):
    """EV element configuration with loaded values."""

    element_type: Literal[ElementType.EV]
    vehicle: VehicleData
    charging: ChargingData
    trip: NotRequired[TripData]
    public_charging: NotRequired[PublicChargingData]
    efficiency: EfficiencyData
    advanced: AdvancedData


__all__ = [
    "CONF_AWAY",
    "CONF_CAPACITY",
    "CONF_CHARGE_LIMIT_COST",
    "CONF_CONNECTED",
    "CONF_CURRENT_SOC",
    "CONF_ENERGY_PER_DISTANCE",
    "CONF_MAX_CHARGE_RATE",
    "CONF_MAX_DISCHARGE_RATE",
    "CONF_MIN_CHARGE_PERCENTAGE",
    "CONF_ODOMETER",
    "CONF_PUBLIC_CHARGING_PRICE",
    "CONF_TRIP_CALENDAR",
    "CONF_TRIP_DUE",
    "CONF_TRIP_OPENED",
    "CONF_TRIP_START",
    "ELEMENT_TYPE",
    "SECTION_ADVANCED",
    "SECTION_CHARGING",
    "SECTION_PUBLIC_CHARGING",
    "SECTION_TRIP",
    "SECTION_VEHICLE",
    "AdvancedConfig",
    "AdvancedData",
    "ChargingConfig",
    "ChargingData",
    "EvConfigData",
    "EvConfigSchema",
    "PublicChargingConfig",
    "PublicChargingData",
    "TripConfig",
    "TripData",
    "VehicleConfig",
    "VehicleData",
]
