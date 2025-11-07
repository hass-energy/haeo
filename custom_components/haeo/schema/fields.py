"""Field metadata definitions for HAEO schema system."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any, Final, Literal

from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import CURRENCY_DOLLAR, UnitOfEnergy, UnitOfPower
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

from custom_components.haeo.data.loader import ConstantLoader, Loader, TimeSeriesLoader

type FieldValidator = vol.All | BooleanSelector | EntitySelector | NumberSelector | SelectSelector


@dataclass(frozen=True)
class FieldMeta(ABC):
    """Base metadata describing schema and data behaviour for a field."""

    field_type: tuple[str | SensorDeviceClass, str]
    loader: Loader

    def create_schema(self, **kwargs: Any) -> FieldValidator:
        """Return the voluptuous validators for this field."""
        return self._get_field_validators(**kwargs)

    @abstractmethod
    def _get_field_validators(self, **kwargs: Any) -> FieldValidator:
        """Return the validators (selector or callable) for this field."""


@dataclass(frozen=True)
class PowerFieldMeta(FieldMeta):
    """Metadata for constant power values."""

    field_type: tuple[Literal[SensorDeviceClass.POWER], Literal["constant"]] = (
        SensorDeviceClass.POWER,
        "constant",
    )
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float](float))

    def _get_field_validators(self, **_kwargs: Any) -> vol.All:
        return vol.All(
            vol.Coerce(float),
            vol.Range(min=0, min_included=True, msg="Value must be positive"),
            NumberSelector(
                NumberSelectorConfig(
                    mode=NumberSelectorMode.BOX,
                    min=0,
                    step=0.01,
                    unit_of_measurement=UnitOfPower.KILO_WATT,
                )
            ),
        )


@dataclass(frozen=True, kw_only=True)
class SensorFieldMeta(FieldMeta):
    """Generic metadata for sensor entity references."""

    device_classes: Sequence[str | SensorDeviceClass]
    multiple: bool
    loader: TimeSeriesLoader = field(default_factory=TimeSeriesLoader)
    field_type: tuple[str | SensorDeviceClass, Literal["sensor"]] = field(init=False)

    def __post_init__(self) -> None:
        """Set field_type based on device_classes after initialization."""
        # Use the first device class as the primary type indicator
        primary_device_class = self.device_classes[0] if self.device_classes else SensorDeviceClass.POWER
        # Use object.__setattr__ because the dataclass is frozen
        object.__setattr__(self, "field_type", (primary_device_class, "sensor"))

    def _get_field_validators(self, **_kwargs: Any) -> EntitySelector:
        return EntitySelector(
            EntitySelectorConfig(
                domain="sensor",
                multiple=self.multiple,
                device_class=list(self.device_classes),
            )
        )


@dataclass(frozen=True)
class EnergyFieldMeta(FieldMeta):
    """Metadata for constant energy values."""

    field_type: tuple[Literal[SensorDeviceClass.ENERGY], Literal["constant"]] = (
        SensorDeviceClass.ENERGY,
        "constant",
    )
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float](float))

    def _get_field_validators(self, **_kwargs: Any) -> vol.All:
        return vol.All(
            vol.Coerce(float),
            vol.Range(min=0, min_included=True, msg="Value must be positive"),
            NumberSelector(
                NumberSelectorConfig(
                    mode=NumberSelectorMode.BOX,
                    min=0,
                    step=0.01,
                    unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                )
            ),
        )


@dataclass(frozen=True)
class PriceFieldMeta(FieldMeta):
    """Metadata for constant price values."""

    field_type: tuple[Literal[SensorDeviceClass.MONETARY], Literal["constant"]] = (
        SensorDeviceClass.MONETARY,
        "constant",
    )
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float](float))

    def _get_field_validators(self, **_kwargs: Any) -> vol.All:
        return vol.All(
            vol.Coerce(float),
            NumberSelector(
                NumberSelectorConfig(
                    mode=NumberSelectorMode.BOX,
                    step=1,
                    unit_of_measurement=f"{CURRENCY_DOLLAR}/{UnitOfEnergy.KILO_WATT_HOUR}",
                )
            ),
        )


@dataclass(frozen=True)
class PercentageFieldMeta(FieldMeta):
    """Metadata for percentage values."""

    field_type: tuple[Literal["%"], Literal["constant"]] = ("%", "constant")
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float](float))

    def _get_field_validators(self, **_kwargs: Any) -> vol.All:
        return vol.All(vol.Coerce(float), vol.Range(min=0, max=100, msg="Value must be between 0 and 100"))


@dataclass(frozen=True)
class BooleanFieldMeta(FieldMeta):
    """Metadata for boolean values."""

    field_type: tuple[Literal["boolean"], Literal["constant"]] = ("boolean", "constant")
    loader: ConstantLoader[bool] = field(default_factory=lambda: ConstantLoader[bool](bool))

    def _get_field_validators(self, **_kwargs: Any) -> vol.All:
        return vol.All(vol.Coerce(bool), BooleanSelector(BooleanSelectorConfig()))


@dataclass(frozen=True)
class ElementNameFieldMeta(FieldMeta):
    """Metadata for selecting existing element names."""

    field_type: tuple[Literal["string"], Literal["constant"]] = ("string", "constant")
    loader: ConstantLoader[str] = field(default_factory=lambda: ConstantLoader[str](str))

    def _get_field_validators(
        self,
        *,
        participants: Sequence[str] | None = None,
        current_element_name: str | None = None,
        **_kwargs: Any,
    ) -> vol.All:
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

    field_type: tuple[Literal["string"], Literal["constant"]] = ("string", "constant")
    loader: ConstantLoader[str] = field(default_factory=lambda: ConstantLoader[str](str))

    def _get_field_validators(self, **_kwargs: Any) -> vol.All:
        return vol.All(vol.Coerce(str), vol.Strip, vol.Length(min=1, msg="Name cannot be empty"))


@dataclass(frozen=True)
class PowerFlowFieldMeta(FieldMeta):
    """Metadata for power flow limits."""

    field_type: tuple[Literal[SensorDeviceClass.POWER], Literal["constant"]] = (
        SensorDeviceClass.POWER,
        "constant",
    )
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float](float))

    def _get_field_validators(self, **_kwargs: Any) -> vol.All:
        return vol.All(
            vol.Coerce(float),
            NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, step=0.01, unit_of_measurement=UnitOfPower.KILO_WATT)
            ),
        )


@dataclass(frozen=True)
class BatterySOCFieldMeta(FieldMeta):
    """Metadata for battery state-of-charge percentages."""

    field_type: tuple[Literal[SensorDeviceClass.BATTERY], Literal["constant"]] = (
        SensorDeviceClass.BATTERY,
        "constant",
    )
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float](float))

    def _get_field_validators(self, **_kwargs: Any) -> vol.All:
        return vol.All(vol.Coerce(float), vol.Range(min=0, max=100, msg="Value must be between 0 and 100"))


ENERGY_SENSORS: Final = [
    SensorDeviceClass.ENERGY,
    SensorDeviceClass.ENERGY_STORAGE,
    SensorDeviceClass.BATTERY,
    SensorDeviceClass.POWER,
]
# Some "Power" forecast sensors like solar seem to be put on sensors that have Energy class rather than Power
POWER_SENSORS: Final = [SensorDeviceClass.POWER, SensorDeviceClass.ENERGY]
BATTERY_SENSORS: Final = [SensorDeviceClass.BATTERY]
PRICE_SENSORS: Final = [SensorDeviceClass.MONETARY]

# Schema mode type aliases (configuration with entity IDs)
PowerFieldSchema = Annotated[float, PowerFieldMeta()]
PowerSensorFieldSchema = Annotated[Sequence[str], SensorFieldMeta(device_classes=POWER_SENSORS, multiple=False)]
PowerSensorsFieldSchema = Annotated[Sequence[str], SensorFieldMeta(device_classes=POWER_SENSORS, multiple=True)]
PowerFlowFieldSchema = Annotated[float, PowerFlowFieldMeta()]
EnergyFieldSchema = Annotated[float, EnergyFieldMeta()]
EnergySensorFieldSchema = Annotated[str, SensorFieldMeta(device_classes=ENERGY_SENSORS, multiple=False)]
EnergySensorsFieldSchema = Annotated[Sequence[str], SensorFieldMeta(device_classes=ENERGY_SENSORS, multiple=True)]
PercentageFieldSchema = Annotated[float, PercentageFieldMeta()]
BooleanFieldSchema = Annotated[bool, BooleanFieldMeta()]
ElementNameFieldSchema = Annotated[str, ElementNameFieldMeta()]
NameFieldSchema = Annotated[str, NameFieldMeta()]
BatterySOCFieldSchema = Annotated[float, BatterySOCFieldMeta()]
BatterySOCSensorFieldSchema = Annotated[str, SensorFieldMeta(device_classes=BATTERY_SENSORS, multiple=False)]
PriceFieldSchema = Annotated[float, PriceFieldMeta()]
PriceSensorsFieldSchema = Annotated[Sequence[str], SensorFieldMeta(device_classes=PRICE_SENSORS, multiple=True)]

# Data mode type aliases (loaded runtime values)
PowerFieldData = Annotated[float, PowerFieldMeta()]
PowerSensorFieldData = Annotated[list[float], SensorFieldMeta(device_classes=POWER_SENSORS, multiple=False)]
PowerSensorsFieldData = Annotated[list[float], SensorFieldMeta(device_classes=POWER_SENSORS, multiple=True)]
PowerFlowFieldData = Annotated[float, PowerFlowFieldMeta()]
EnergyFieldData = Annotated[float, EnergyFieldMeta()]
EnergySensorFieldData = Annotated[list[float], SensorFieldMeta(device_classes=ENERGY_SENSORS, multiple=False)]
EnergySensorsFieldData = Annotated[list[float], SensorFieldMeta(device_classes=ENERGY_SENSORS, multiple=True)]
PercentageFieldData = Annotated[float, PercentageFieldMeta()]
BooleanFieldData = Annotated[bool, BooleanFieldMeta()]
ElementNameFieldData = Annotated[str, ElementNameFieldMeta()]
NameFieldData = Annotated[str, NameFieldMeta()]
BatterySOCFieldData = Annotated[float, BatterySOCFieldMeta()]
BatterySOCSensorFieldData = Annotated[list[float], SensorFieldMeta(device_classes=BATTERY_SENSORS, multiple=False)]
PriceFieldData = Annotated[float, PriceFieldMeta()]
PriceSensorsFieldData = Annotated[list[float], SensorFieldMeta(device_classes=PRICE_SENSORS, multiple=True)]
