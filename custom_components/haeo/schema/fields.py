"""Field metadata definitions for HAEO schema system."""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from numbers import Real
from typing import Annotated, Any, Literal

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

from custom_components.haeo.data.loader import (
    ConstantLoader,
    ForecastAndSensorLoader,
    ForecastLoader,
    Loader,
    SensorLoader,
)

type FieldValidator = vol.All | BooleanSelector | EntitySelector | NumberSelector | SelectSelector
type FieldValidatorResult = FieldValidator | Mapping[str, FieldValidator]


@dataclass(frozen=True)
class FieldMeta(ABC):
    """Base metadata describing schema and data behaviour for a field."""

    field_type: tuple[str | SensorDeviceClass, str]
    loader: Loader

    def create_schema(self, **kwargs: Any) -> FieldValidatorResult:
        """Return the voluptuous validators for this field."""
        return self._get_field_validators(**kwargs)

    @abstractmethod
    def _get_field_validators(self, **kwargs: Any) -> FieldValidatorResult:
        """Return the validators (selector or callable) for this field."""


@dataclass(frozen=True)
class PowerFieldMeta(FieldMeta):
    """Metadata for constant power values."""

    field_type: tuple[Literal[SensorDeviceClass.POWER], Literal["constant"]] = (
        SensorDeviceClass.POWER,
        "constant",
    )
    loader: ConstantLoader[Real] = field(default_factory=lambda: ConstantLoader[Real](Real))

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


@dataclass(frozen=True)
class PowerSensorsFieldMeta(FieldMeta):
    """Metadata for power sensor entity references."""

    field_type: tuple[Literal[SensorDeviceClass.POWER], Literal["sensor"]] = (
        SensorDeviceClass.POWER,
        "sensor",
    )
    loader: SensorLoader = field(default_factory=lambda: SensorLoader())

    def _get_field_validators(self, **_kwargs: Any) -> EntitySelector:
        return EntitySelector(
            EntitySelectorConfig(domain="sensor", multiple=True, device_class=[SensorDeviceClass.POWER])
        )


@dataclass(frozen=True)
class PowerForecastsFieldMeta(FieldMeta):
    """Metadata for power forecast entity references."""

    field_type: tuple[Literal[SensorDeviceClass.POWER], Literal["forecast"]] = (
        SensorDeviceClass.POWER,
        "forecast",
    )
    loader: ForecastLoader = field(default_factory=lambda: ForecastLoader())

    def _get_field_validators(self, **_kwargs: Any) -> EntitySelector:
        return EntitySelector(
            EntitySelectorConfig(
                domain="sensor",
                multiple=True,
                device_class=[SensorDeviceClass.POWER, SensorDeviceClass.ENERGY],
            )
        )


@dataclass(frozen=True)
class EnergyFieldMeta(FieldMeta):
    """Metadata for constant energy values."""

    field_type: tuple[Literal[SensorDeviceClass.ENERGY], Literal["constant"]] = (
        SensorDeviceClass.ENERGY,
        "constant",
    )
    loader: ConstantLoader[Real] = field(default_factory=lambda: ConstantLoader[Real](Real))

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
class EnergySensorsFieldMeta(FieldMeta):
    """Metadata for energy sensor entity references."""

    field_type: tuple[Literal[SensorDeviceClass.ENERGY], Literal["sensor"]] = (
        SensorDeviceClass.ENERGY,
        "sensor",
    )
    loader: SensorLoader = field(default_factory=lambda: SensorLoader())

    def _get_field_validators(self, **_kwargs: Any) -> EntitySelector:
        return EntitySelector(
            EntitySelectorConfig(
                domain="sensor",
                multiple=True,
                device_class=[SensorDeviceClass.BATTERY, SensorDeviceClass.ENERGY_STORAGE],
            )
        )


@dataclass(frozen=True)
class PriceFieldMeta(FieldMeta):
    """Metadata for constant price values."""

    field_type: tuple[Literal[SensorDeviceClass.MONETARY], Literal["constant"]] = (
        SensorDeviceClass.MONETARY,
        "constant",
    )
    loader: ConstantLoader[Real] = field(default_factory=lambda: ConstantLoader[Real](Real))

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
class PriceSensorsFieldMeta(FieldMeta):
    """Metadata for live price sensor entity references."""

    field_type: tuple[Literal[SensorDeviceClass.MONETARY], Literal["sensor"]] = (
        SensorDeviceClass.MONETARY,
        "sensor",
    )
    loader: SensorLoader = field(default_factory=lambda: SensorLoader())

    def _get_field_validators(self, **_kwargs: Any) -> EntitySelector:
        return EntitySelector(
            EntitySelectorConfig(domain="sensor", multiple=True, device_class=[SensorDeviceClass.MONETARY])
        )


@dataclass(frozen=True)
class PriceForecastsFieldMeta(FieldMeta):
    """Metadata for price forecast entity references."""

    field_type: tuple[Literal[SensorDeviceClass.MONETARY], Literal["forecast"]] = (
        SensorDeviceClass.MONETARY,
        "forecast",
    )
    loader: ForecastLoader = field(default_factory=lambda: ForecastLoader())

    def _get_field_validators(self, **_kwargs: Any) -> EntitySelector:
        return EntitySelector(EntitySelectorConfig(domain="sensor", multiple=True))


@dataclass(frozen=True)
class PricesSensorsAndForecastsFieldMeta(FieldMeta):
    """Metadata for live and forecast price configuration."""

    field_type: tuple[Literal[SensorDeviceClass.MONETARY], Literal["live_forecast"]] = (
        SensorDeviceClass.MONETARY,
        "live_forecast",
    )
    loader: ForecastAndSensorLoader = field(default_factory=lambda: ForecastAndSensorLoader())

    def _get_field_validators(self, **_kwargs: Any) -> Mapping[str, EntitySelector]:
        return {
            "live": EntitySelector(EntitySelectorConfig(domain="sensor", multiple=True)),
            "forecast": EntitySelector(EntitySelectorConfig(domain="sensor", multiple=True)),
        }


@dataclass(frozen=True)
class PercentageFieldMeta(FieldMeta):
    """Metadata for percentage values."""

    field_type: tuple[Literal["%"], Literal["constant"]] = ("%", "constant")
    loader: ConstantLoader[Real] = field(default_factory=lambda: ConstantLoader[Real](Real))

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
    loader: ConstantLoader[Real] = field(default_factory=lambda: ConstantLoader[Real](Real))

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
    loader: ConstantLoader[Real] = field(default_factory=lambda: ConstantLoader[Real](Real))

    def _get_field_validators(self, **_kwargs: Any) -> vol.All:
        return vol.All(vol.Coerce(float), vol.Range(min=0, max=100, msg="Value must be between 0 and 100"))


@dataclass(frozen=True)
class BatterySOCSensorFieldMeta(FieldMeta):
    """Metadata for battery state-of-charge sensors."""

    field_type: tuple[Literal[SensorDeviceClass.BATTERY], Literal["sensor"]] = (
        SensorDeviceClass.BATTERY,
        "sensor",
    )
    loader: SensorLoader = field(default_factory=lambda: SensorLoader())

    def _get_field_validators(self, **_kwargs: Any) -> EntitySelector:
        return EntitySelector(EntitySelectorConfig(domain="sensor", device_class=[SensorDeviceClass.BATTERY]))


# Schema mode type aliases (configuration with entity IDs)
PowerFieldSchema = Annotated[float, PowerFieldMeta()]
PowerSensorsFieldSchema = Annotated[Sequence[str], PowerSensorsFieldMeta()]
PowerForecastsFieldSchema = Annotated[Sequence[str], PowerForecastsFieldMeta()]
PowerFlowFieldSchema = Annotated[float, PowerFlowFieldMeta()]
EnergyFieldSchema = Annotated[float, EnergyFieldMeta()]
EnergySensorsFieldSchema = Annotated[Sequence[str], EnergySensorsFieldMeta()]
PercentageFieldSchema = Annotated[float, PercentageFieldMeta()]
BooleanFieldSchema = Annotated[bool, BooleanFieldMeta()]
ElementNameFieldSchema = Annotated[str, ElementNameFieldMeta()]
NameFieldSchema = Annotated[str, NameFieldMeta()]
BatterySOCFieldSchema = Annotated[float, BatterySOCFieldMeta()]
BatterySOCSensorFieldSchema = Annotated[str, BatterySOCSensorFieldMeta()]
PriceFieldSchema = Annotated[float, PriceFieldMeta()]
PriceSensorsFieldSchema = Annotated[Sequence[str], PriceSensorsFieldMeta()]
PriceForecastsFieldSchema = Annotated[Sequence[str], PriceForecastsFieldMeta()]
PricesSensorsAndForecastsFieldSchema = Annotated[
    dict[Literal["live", "forecast"], Sequence[str]], PricesSensorsAndForecastsFieldMeta()
]

# Data mode type aliases (loaded runtime values)
PowerFieldData = Annotated[float, PowerFieldMeta()]
PowerSensorsFieldData = Annotated[float, PowerSensorsFieldMeta()]
PowerForecastsFieldData = Annotated[list[float], PowerForecastsFieldMeta()]
PowerFlowFieldData = Annotated[float, PowerFlowFieldMeta()]
EnergyFieldData = Annotated[float, EnergyFieldMeta()]
EnergySensorsFieldData = Annotated[float, EnergySensorsFieldMeta()]
PercentageFieldData = Annotated[float, PercentageFieldMeta()]
BooleanFieldData = Annotated[bool, BooleanFieldMeta()]
ElementNameFieldData = Annotated[str, ElementNameFieldMeta()]
NameFieldData = Annotated[str, NameFieldMeta()]
BatterySOCFieldData = Annotated[float, BatterySOCFieldMeta()]
BatterySOCSensorFieldData = Annotated[float, BatterySOCSensorFieldMeta()]
PriceFieldData = Annotated[float, PriceFieldMeta()]
PriceSensorsFieldData = Annotated[float, PriceSensorsFieldMeta()]
PriceForecastsFieldData = Annotated[list[float], PriceForecastsFieldMeta()]
PricesSensorsAndForecastsFieldData = Annotated[list[float], PricesSensorsAndForecastsFieldMeta()]
