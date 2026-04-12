"""EV element schema definitions."""

from typing import Annotated, Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import ConstantValue, EntityValue, NoneValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.field_hints import FieldHint, SectionHints
from custom_components.haeo.core.schema.sections import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    ConnectedCommonConfig,
    ConnectedCommonData,
    EfficiencyConfig,
    EfficiencyData,
    PowerLimitsConfig,
    PowerLimitsData,
)

ELEMENT_TYPE = ElementType.EV

# Section names
SECTION_VEHICLE: Final = "vehicle"
SECTION_CHARGING: Final = "charging"
SECTION_TRIP: Final = "trip"
SECTION_PUBLIC_CHARGING: Final = "public_charging"

# Vehicle section field names
CONF_CAPACITY: Final = "capacity"
CONF_ENERGY_PER_DISTANCE: Final = "energy_per_distance"
CONF_CURRENT_SOC: Final = "current_soc"

# Charging section field names
CONF_MAX_CHARGE_RATE: Final = "max_charge_rate"
CONF_MAX_DISCHARGE_RATE: Final = "max_discharge_rate"

# Trip section field names
CONF_CONNECTED: Final = "connected"

# Public charging section field names
CONF_PUBLIC_CHARGING_PRICE: Final = "public_charging_price"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        CONF_CONNECTED,
        CONF_MAX_DISCHARGE_RATE,
        CONF_MAX_POWER_SOURCE_TARGET,
        CONF_MAX_POWER_TARGET_SOURCE,
        CONF_EFFICIENCY_SOURCE_TARGET,
        CONF_EFFICIENCY_TARGET_SOURCE,
        CONF_PUBLIC_CHARGING_PRICE,
    }
)


# --- Vehicle section ---


class VehicleConfig(TypedDict):
    """Vehicle details configuration."""

    capacity: EntityValue | ConstantValue
    energy_per_distance: EntityValue | ConstantValue
    current_soc: EntityValue


class VehicleData(TypedDict):
    """Loaded vehicle details."""

    capacity: NDArray[np.floating[Any]]
    energy_per_distance: float
    current_soc: float


# --- Charging section ---


class ChargingConfig(TypedDict):
    """Charging rate configuration."""

    max_charge_rate: EntityValue | ConstantValue
    max_discharge_rate: NotRequired[EntityValue | ConstantValue | NoneValue]


class ChargingData(TypedDict):
    """Loaded charging rate values."""

    max_charge_rate: NDArray[np.floating[Any]] | float
    max_discharge_rate: NotRequired[NDArray[np.floating[Any]] | float]


# --- Trip section ---


class TripConfig(TypedDict, total=False):
    """Trip availability configuration."""

    connected: EntityValue | ConstantValue | NoneValue


class TripData(TypedDict, total=False):
    """Loaded trip availability values."""

    connected: NDArray[np.floating[Any]] | float


# --- Public charging section ---


class PublicChargingConfig(TypedDict, total=False):
    """Public charging pricing configuration."""

    public_charging_price: EntityValue | ConstantValue | NoneValue


class PublicChargingData(TypedDict, total=False):
    """Loaded public charging pricing values."""

    public_charging_price: NDArray[np.floating[Any]] | float


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
                    output_type=OutputType.ENERGY,
                    time_series=False,
                ),
                CONF_CURRENT_SOC: FieldHint(
                    output_type=OutputType.STATE_OF_CHARGE,
                    time_series=False,
                    step=0.1,
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
                    direction="+",
                    time_series=True,
                    step=0.1,
                ),
                CONF_MAX_DISCHARGE_RATE: FieldHint(
                    output_type=OutputType.POWER,
                    direction="-",
                    time_series=True,
                    step=0.1,
                ),
            }
        ),
    ]
    trip: NotRequired[
        Annotated[
            TripConfig,
            SectionHints(
                {
                    CONF_CONNECTED: FieldHint(
                        output_type=OutputType.AVAILABILITY,
                        time_series=True,
                        boundaries=True,
                        default_mode="value",
                        default_value=1.0,
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
                    ),
                }
            ),
        ]
    ]
    power_limits: Annotated[
        PowerLimitsConfig,
        SectionHints(
            {
                CONF_MAX_POWER_SOURCE_TARGET: FieldHint(
                    output_type=OutputType.POWER_LIMIT,
                    direction="+",
                    time_series=True,
                ),
                CONF_MAX_POWER_TARGET_SOURCE: FieldHint(
                    output_type=OutputType.POWER_LIMIT,
                    direction="-",
                    time_series=True,
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


class EvConfigData(ConnectedCommonData):
    """EV element configuration with loaded values."""

    element_type: Literal[ElementType.EV]
    vehicle: VehicleData
    charging: ChargingData
    trip: NotRequired[TripData]
    public_charging: NotRequired[PublicChargingData]
    power_limits: PowerLimitsData
    efficiency: EfficiencyData


__all__ = [
    "CONF_CAPACITY",
    "CONF_CONNECTED",
    "CONF_CURRENT_SOC",
    "CONF_ENERGY_PER_DISTANCE",
    "CONF_MAX_CHARGE_RATE",
    "CONF_MAX_DISCHARGE_RATE",
    "CONF_PUBLIC_CHARGING_PRICE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_CHARGING",
    "SECTION_PUBLIC_CHARGING",
    "SECTION_TRIP",
    "SECTION_VEHICLE",
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
