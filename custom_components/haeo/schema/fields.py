"""Field metadata definitions for HAEO schema system.

This module provides composable metadata types for defining field behavior:

- **Validators**: Define schema validation and UI selectors
- **Loaders**: Specify how field values are loaded at runtime
- **Default**: Provides default values for config flow forms

These metadata types compose via `Annotated` to define complete field behavior:

    PowerFieldSchema = Annotated[float, PositiveKW(), ConstantFloat()]

The `compose_field()` function in schema/__init__.py extracts and combines
these metadata into a unified `FieldSpec` for use by schema generation and loading.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Any, Final, Unpack

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

from custom_components.haeo.data.loader.extractors import EntityMetadata

from .params import SchemaParams
from .util import UnitSpec

# Default metadata type


@dataclass(frozen=True, kw_only=True)
class Default:
    """Default value marker for field composition.

    Specifies the default value shown in config flow UI when adding new elements.

    Examples:
        Annotated[float, PositiveKW(), ConstantFloat(), Default(value=5.0)]

    """

    value: float | bool


# Loader metadata types


@dataclass(frozen=True)
class LoaderMeta:
    """Base class for loader metadata markers."""


@dataclass(frozen=True)
class ConstantFloat(LoaderMeta):
    """Marker for constant float values loaded directly from config."""


@dataclass(frozen=True)
class ConstantBool(LoaderMeta):
    """Marker for constant boolean values loaded directly from config."""


@dataclass(frozen=True)
class ConstantStr(LoaderMeta):
    """Marker for constant string values loaded directly from config."""


@dataclass(frozen=True)
class TimeSeries(LoaderMeta):
    """Marker for time series data loaded from sensors/forecasts."""


# Validator metadata types


@dataclass(frozen=True)
class Validator(ABC):
    """Base class for schema validators.

    Validators define both validation rules and UI selectors for config flow.
    """

    @abstractmethod
    def create_schema(self, **schema_params: Unpack[SchemaParams]) -> vol.All:
        """Return voluptuous validators for this field."""


@dataclass(frozen=True)
class PositiveKW(Validator):
    """Validates positive power values in kilowatts."""

    def create_schema(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        """Return voluptuous validators for positive power in kW."""
        return vol.All(
            vol.Coerce(float),
            vol.Range(min=0, min_included=True, msg="Value must be positive"),
            NumberSelector(
                NumberSelectorConfig(
                    mode=NumberSelectorMode.BOX,
                    min=0,
                    step="any",
                    unit_of_measurement=UnitOfPower.KILO_WATT,
                )
            ),
        )


@dataclass(frozen=True)
class AnyKW(Validator):
    """Validates power flow values (positive or negative) in kilowatts."""

    def create_schema(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        """Return voluptuous validators for power flow in kW."""
        return vol.All(
            vol.Coerce(float),
            NumberSelector(
                NumberSelectorConfig(
                    mode=NumberSelectorMode.BOX,
                    step="any",
                    unit_of_measurement=UnitOfPower.KILO_WATT,
                )
            ),
        )


@dataclass(frozen=True)
class PositiveKWH(Validator):
    """Validates positive energy values in kilowatt-hours."""

    def create_schema(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        """Return voluptuous validators for positive energy in kWh."""
        return vol.All(
            vol.Coerce(float),
            vol.Range(min=0, min_included=True, msg="Value must be positive"),
            NumberSelector(
                NumberSelectorConfig(
                    mode=NumberSelectorMode.BOX,
                    min=0,
                    step="any",
                    unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                )
            ),
        )


@dataclass(frozen=True)
class Price(Validator):
    """Validates price values in $/kWh."""

    def create_schema(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        """Return voluptuous validators for price in $/kWh."""
        return vol.All(
            vol.Coerce(float),
            NumberSelector(
                NumberSelectorConfig(
                    mode=NumberSelectorMode.BOX,
                    step="any",
                    unit_of_measurement=f"{CURRENCY_DOLLAR}/{UnitOfEnergy.KILO_WATT_HOUR}",
                )
            ),
        )


@dataclass(frozen=True)
class Percentage(Validator):
    """Validates percentage values (0-100)."""

    def create_schema(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        """Return voluptuous validators for percentage."""
        return vol.All(
            vol.Coerce(float),
            vol.Range(min=0, max=100, msg="Value must be between 0 and 100"),
        )


@dataclass(frozen=True)
class BatterySOC(Validator):
    """Validates battery state-of-charge percentages (0-100)."""

    def create_schema(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        """Return voluptuous validators for battery SOC percentage."""
        return vol.All(
            vol.Coerce(float),
            vol.Range(min=0, max=100, msg="Value must be between 0 and 100"),
        )


@dataclass(frozen=True)
class Boolean(Validator):
    """Validates boolean toggle values."""

    def create_schema(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        """Return voluptuous validators for boolean."""
        return vol.All(vol.Coerce(bool), BooleanSelector(BooleanSelectorConfig()))


@dataclass(frozen=True)
class Name(Validator):
    """Validates free-form name strings."""

    def create_schema(self, **_schema_params: Unpack[SchemaParams]) -> vol.All:
        """Return voluptuous validators for name string."""
        return vol.All(
            vol.Coerce(str),
            vol.Strip,
            vol.Length(min=1, msg="Name cannot be empty"),
        )


@dataclass(frozen=True)
class ElementName(Validator):
    """Validates element name selection from available participants."""

    def create_schema(self, **schema_params: Unpack[SchemaParams]) -> vol.All:
        """Return voluptuous validators for element name selection."""
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
class EntitySelect(Validator):
    """Validates entity selection with unit-based filtering."""

    accepted_units: UnitSpec | list[UnitSpec]
    multiple: bool = False

    def create_schema(self, **schema_params: Unpack[SchemaParams]) -> vol.All:
        """Return voluptuous validators for entity selection."""
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


# Unit sets for sensor filtering

POWER_UNITS: Final = UnitOfPower
ENERGY_UNITS: Final = UnitOfEnergy
BATTERY_UNITS: Final = [PERCENTAGE]
PERCENTAGE_UNITS: Final = [PERCENTAGE]
PRICE_UNITS: Final[list[UnitSpec]] = [("*", "/", unit.value) for unit in UnitOfEnergy]


# Field type aliases
# Schema mode: entity IDs for configuration
# Data mode: loaded values for runtime

PowerFieldSchema = Annotated[float, PositiveKW(), ConstantFloat()]
PowerFieldData = Annotated[float, PositiveKW(), ConstantFloat()]

PowerFlowFieldSchema = Annotated[float, AnyKW(), ConstantFloat()]
PowerFlowFieldData = Annotated[float, AnyKW(), ConstantFloat()]

EnergyFieldSchema = Annotated[float, PositiveKWH(), ConstantFloat()]
EnergyFieldData = Annotated[float, PositiveKWH(), ConstantFloat()]

PercentageFieldSchema = Annotated[float, Percentage(), ConstantFloat()]
PercentageFieldData = Annotated[float, Percentage(), ConstantFloat()]

BooleanFieldSchema = Annotated[bool, Boolean(), ConstantBool()]
BooleanFieldData = Annotated[bool, Boolean(), ConstantBool()]

NameFieldSchema = Annotated[str, Name(), ConstantStr()]
NameFieldData = Annotated[str, Name(), ConstantStr()]

ElementNameFieldSchema = Annotated[str, ElementName(), ConstantStr()]
ElementNameFieldData = Annotated[str, ElementName(), ConstantStr()]

BatterySOCFieldSchema = Annotated[float, BatterySOC(), ConstantFloat()]
BatterySOCFieldData = Annotated[float, BatterySOC(), ConstantFloat()]

PriceFieldSchema = Annotated[float, Price(), ConstantFloat()]
PriceFieldData = Annotated[float, Price(), ConstantFloat()]

PowerSensorFieldSchema = Annotated[str, EntitySelect(POWER_UNITS), TimeSeries()]
PowerSensorFieldData = Annotated[list[float], EntitySelect(POWER_UNITS), TimeSeries()]

PowerSensorsFieldSchema = Annotated[Sequence[str], EntitySelect(POWER_UNITS, multiple=True), TimeSeries()]
PowerSensorsFieldData = Annotated[list[float], EntitySelect(POWER_UNITS, multiple=True), TimeSeries()]

EnergySensorFieldSchema = Annotated[str, EntitySelect(ENERGY_UNITS), TimeSeries()]
EnergySensorFieldData = Annotated[list[float], EntitySelect(ENERGY_UNITS), TimeSeries()]

EnergySensorsFieldSchema = Annotated[Sequence[str], EntitySelect(ENERGY_UNITS, multiple=True), TimeSeries()]
EnergySensorsFieldData = Annotated[list[float], EntitySelect(ENERGY_UNITS, multiple=True), TimeSeries()]

PercentageSensorFieldSchema = Annotated[str, EntitySelect(PERCENTAGE_UNITS), TimeSeries()]
PercentageSensorFieldData = Annotated[list[float], EntitySelect(PERCENTAGE_UNITS), TimeSeries()]

BatterySOCSensorFieldSchema = Annotated[str, EntitySelect(BATTERY_UNITS), TimeSeries()]
BatterySOCSensorFieldData = Annotated[list[float], EntitySelect(BATTERY_UNITS), TimeSeries()]

PriceSensorsFieldSchema = Annotated[Sequence[str], EntitySelect(PRICE_UNITS, multiple=True), TimeSeries()]
PriceSensorsFieldData = Annotated[list[float], EntitySelect(PRICE_UNITS, multiple=True), TimeSeries()]
