"""Field metadata definitions for HAEO schema system."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any, Final, Literal, Unpack

from homeassistant.const import CURRENCY_DOLLAR, PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from custom_components.haeo.data.loader import ConstantLoader, HistoricalLoadLoader, Loader, TimeSeriesLoader
from custom_components.haeo.data.loader.extractors import EntityMetadata

from .params import SchemaParams
from .util import UnitSpec


@dataclass(frozen=True)
class FieldMeta(ABC):
    """Base metadata describing schema and data behaviour for a field."""

    field_type: str
    loader: Loader

    def create_schema(self, **schema_params: Unpack[SchemaParams]) -> vol.All:
        """Return the voluptuous validators for this field."""
        return self._get_field_validators(**schema_params)

    @abstractmethod
    def _get_field_validators(self, **schema_params: Unpack[SchemaParams]) -> vol.All:
        """Return the validators (selector or callable) for this field."""


@dataclass(frozen=True)
class PowerFieldMeta(FieldMeta):
    """Metadata for constant power values."""

    field_type: Literal["constant"] = "constant"
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float](float))

    def _get_field_validators(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        return vol.All(
            vol.Coerce(float),
            vol.Range(min=0, min_included=True, msg="Value must be positive"),
            NumberSelector(
                NumberSelectorConfig(
                    mode=NumberSelectorMode.BOX,
                    min=0,
                    step=0.001,
                    unit_of_measurement=UnitOfPower.KILO_WATT,
                )
            ),
        )


@dataclass(frozen=True, kw_only=True)
class SensorFieldMeta(FieldMeta):
    """Generic metadata for sensor entity references."""

    accepted_units: UnitSpec | list[UnitSpec]
    multiple: bool
    loader: TimeSeriesLoader = field(default_factory=TimeSeriesLoader)
    field_type: Literal["sensor"] = "sensor"

    def _get_field_validators(self, **schema_params: Unpack[SchemaParams]) -> vol.All:
        """Return entity selector with unit-based filtering."""
        # Filter incompatible entities based on accepted_units
        entity_metadata: Sequence[EntityMetadata] = schema_params.get("entity_metadata", [])
        incompatible_entities: list[str] = [
            v.entity_id for v in entity_metadata if not v.is_compatible_with(self.accepted_units)
        ]

        return vol.All(
            EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=self.multiple,
                    exclude_entities=incompatible_entities,
                )
            ),
        )


@dataclass(frozen=True)
class EnergyFieldMeta(FieldMeta):
    """Metadata for constant energy values."""

    field_type: Literal["constant"] = "constant"
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float](float))

    def _get_field_validators(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        return vol.All(
            vol.Coerce(float),
            vol.Range(min=0, min_included=True, msg="Value must be positive"),
            NumberSelector(
                NumberSelectorConfig(
                    mode=NumberSelectorMode.BOX,
                    min=0,
                    step=0.001,
                    unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                )
            ),
        )


@dataclass(frozen=True)
class PriceFieldMeta(FieldMeta):
    """Metadata for constant price values."""

    field_type: Literal["constant"] = "constant"
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float](float))

    def _get_field_validators(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        return vol.All(
            vol.Coerce(float),
            NumberSelector(
                NumberSelectorConfig(
                    mode=NumberSelectorMode.BOX,
                    step=0.001,
                    unit_of_measurement=f"{CURRENCY_DOLLAR}/{UnitOfEnergy.KILO_WATT_HOUR}",
                )
            ),
        )


@dataclass(frozen=True)
class PercentageFieldMeta(FieldMeta):
    """Metadata for percentage values."""

    field_type: Literal["constant"] = "constant"
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float](float))

    def _get_field_validators(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        return vol.All(vol.Coerce(float), vol.Range(min=0, max=100, msg="Value must be between 0 and 100"))


@dataclass(frozen=True)
class BooleanFieldMeta(FieldMeta):
    """Metadata for boolean values."""

    field_type: Literal["constant"] = "constant"
    loader: ConstantLoader[bool] = field(default_factory=lambda: ConstantLoader[bool](bool))

    def _get_field_validators(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        return vol.All(vol.Coerce(bool), BooleanSelector(BooleanSelectorConfig()))


@dataclass(frozen=True)
class ElementNameFieldMeta(FieldMeta):
    """Metadata for selecting existing element names."""

    field_type: Literal["constant"] = "constant"
    loader: ConstantLoader[str] = field(default_factory=lambda: ConstantLoader[str](str))

    def _get_field_validators(self, **schema_params: Unpack[SchemaParams]) -> vol.All:
        participants: Sequence[str] | None = schema_params.get("participants")
        current_element_name: str | None = schema_params.get("current_element_name")

        participants_list = list(participants or [])
        if current_element_name and current_element_name not in participants_list:
            participants_list.append(current_element_name)

        validators: list[Any] = [
            vol.Coerce(str),
            vol.Strip,
            vol.Length(min=1, msg="Element name cannot be empty"),
        ]

        if participants_list:
            options: list[SelectOptionDict] = [
                SelectOptionDict(value=participant, label=participant) for participant in participants_list
            ]
            validators.append(SelectSelector(SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)))

        return vol.All(*validators)


@dataclass(frozen=True)
class NameFieldMeta(FieldMeta):
    """Metadata for free-form name values."""

    field_type: Literal["constant"] = "constant"
    loader: ConstantLoader[str] = field(default_factory=lambda: ConstantLoader[str](str))

    def _get_field_validators(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        return vol.All(vol.Coerce(str), vol.Strip, vol.Length(min=1, msg="Name cannot be empty"))


@dataclass(frozen=True)
class PowerFlowFieldMeta(FieldMeta):
    """Metadata for power flow limits."""

    field_type: Literal["constant"] = "constant"
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float](float))

    def _get_field_validators(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        return vol.All(
            vol.Coerce(float),
            NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, step=0.001, unit_of_measurement=UnitOfPower.KILO_WATT)
            ),
        )


@dataclass(frozen=True)
class BatterySOCFieldMeta(FieldMeta):
    """Metadata for battery state-of-charge percentages."""

    field_type: Literal["constant"] = "constant"
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float](float))

    def _get_field_validators(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        return vol.All(vol.Coerce(float), vol.Range(min=0, max=100, msg="Value must be between 0 and 100"))


# Forecast source options
FORECAST_SOURCE_ENERGY_TAB: Final = "energy_tab"
FORECAST_SOURCE_CUSTOM_SENSOR: Final = "custom_sensor"


@dataclass(frozen=True)
class ForecastSourceFieldMeta(FieldMeta):
    """Metadata for forecast source selection (energy_tab or custom_sensor)."""

    field_type: Literal["constant"] = "constant"
    loader: ConstantLoader[str] = field(default_factory=lambda: ConstantLoader[str](str))

    def _get_field_validators(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        options: list[SelectOptionDict] = [
            SelectOptionDict(value=FORECAST_SOURCE_ENERGY_TAB, label="Energy Tab"),
            SelectOptionDict(value=FORECAST_SOURCE_CUSTOM_SENSOR, label="Custom Sensor"),
        ]
        return vol.All(
            vol.Coerce(str),
            vol.In([FORECAST_SOURCE_ENERGY_TAB, FORECAST_SOURCE_CUSTOM_SENSOR]),
            SelectSelector(SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)),
        )


@dataclass(frozen=True)
class HistoryDaysFieldMeta(FieldMeta):
    """Metadata for number of days of historical data to fetch.

    Uses HistoricalLoadLoader to fetch data from the Energy dashboard.
    """

    field_type: Literal["historical"] = "historical"
    loader: HistoricalLoadLoader = field(default_factory=HistoricalLoadLoader)

    def _get_field_validators(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        return vol.All(
            vol.Coerce(int),
            vol.Range(min=1, max=30, msg="Value must be between 1 and 30 days"),
            NumberSelector(
                NumberSelectorConfig(
                    mode=NumberSelectorMode.BOX,
                    min=1,
                    max=30,
                    step=1,
                    unit_of_measurement="days",
                )
            ),
        )


# Define unit sets for sensor filtering
POWER_UNITS: Final = UnitOfPower
ENERGY_UNITS: Final = UnitOfEnergy
BATTERY_UNITS: Final = [PERCENTAGE]
PERCENTAGE_UNITS: Final = [PERCENTAGE]
# For composite patterns, create tuples for each energy unit
PRICE_UNITS: Final[list[UnitSpec]] = [("*", "/", unit.value) for unit in UnitOfEnergy]

# Schema mode type aliases (configuration with entity IDs)
PowerFieldSchema = Annotated[float, PowerFieldMeta()]
PowerSensorFieldSchema = Annotated[Sequence[str], SensorFieldMeta(accepted_units=POWER_UNITS, multiple=False)]
PowerSensorsFieldSchema = Annotated[Sequence[str], SensorFieldMeta(accepted_units=POWER_UNITS, multiple=True)]
PowerFlowFieldSchema = Annotated[float, PowerFlowFieldMeta()]
EnergyFieldSchema = Annotated[float, EnergyFieldMeta()]
EnergySensorFieldSchema = Annotated[str, SensorFieldMeta(accepted_units=ENERGY_UNITS, multiple=False)]
EnergySensorsFieldSchema = Annotated[Sequence[str], SensorFieldMeta(accepted_units=ENERGY_UNITS, multiple=True)]
PercentageFieldSchema = Annotated[float, PercentageFieldMeta()]
PercentageSensorFieldSchema = Annotated[str, SensorFieldMeta(accepted_units=PERCENTAGE_UNITS, multiple=False)]
BooleanFieldSchema = Annotated[bool, BooleanFieldMeta()]
ElementNameFieldSchema = Annotated[str, ElementNameFieldMeta()]
NameFieldSchema = Annotated[str, NameFieldMeta()]
BatterySOCFieldSchema = Annotated[float, BatterySOCFieldMeta()]
BatterySOCSensorFieldSchema = Annotated[str, SensorFieldMeta(accepted_units=BATTERY_UNITS, multiple=False)]
PriceFieldSchema = Annotated[float, PriceFieldMeta()]
PriceSensorsFieldSchema = Annotated[Sequence[str], SensorFieldMeta(accepted_units=PRICE_UNITS, multiple=True)]

# Data mode type aliases (loaded runtime values)
PowerFieldData = Annotated[float, PowerFieldMeta()]
PowerSensorFieldData = Annotated[list[float], SensorFieldMeta(accepted_units=POWER_UNITS, multiple=False)]
PowerSensorsFieldData = Annotated[list[float], SensorFieldMeta(accepted_units=POWER_UNITS, multiple=True)]
PowerFlowFieldData = Annotated[float, PowerFlowFieldMeta()]
EnergyFieldData = Annotated[float, EnergyFieldMeta()]
EnergySensorFieldData = Annotated[list[float], SensorFieldMeta(accepted_units=ENERGY_UNITS, multiple=False)]
EnergySensorsFieldData = Annotated[list[float], SensorFieldMeta(accepted_units=ENERGY_UNITS, multiple=True)]
PercentageFieldData = Annotated[float, PercentageFieldMeta()]
PercentageSensorFieldData = Annotated[list[float], SensorFieldMeta(accepted_units=PERCENTAGE_UNITS, multiple=False)]
BooleanFieldData = Annotated[bool, BooleanFieldMeta()]
ElementNameFieldData = Annotated[str, ElementNameFieldMeta()]
NameFieldData = Annotated[str, NameFieldMeta()]
BatterySOCFieldData = Annotated[float, BatterySOCFieldMeta()]
BatterySOCSensorFieldData = Annotated[list[float], SensorFieldMeta(accepted_units=BATTERY_UNITS, multiple=False)]
PriceFieldData = Annotated[float, PriceFieldMeta()]
PriceSensorsFieldData = Annotated[list[float], SensorFieldMeta(accepted_units=PRICE_UNITS, multiple=True)]
ForecastSourceFieldSchema = Annotated[str, ForecastSourceFieldMeta()]
ForecastSourceFieldData = Annotated[str, ForecastSourceFieldMeta()]
HistoryDaysFieldSchema = Annotated[int, HistoryDaysFieldMeta()]
HistoryDaysFieldData = Annotated[list[float], HistoryDaysFieldMeta()]
