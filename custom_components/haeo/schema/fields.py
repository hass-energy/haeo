"""Field types for HAEO type system using Annotated types."""

from abc import ABC
from collections.abc import Sequence
from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class FieldMeta(ABC):
    """Base class for unified field metadata.

    This metadata serves both Schema and Data modes:
    - Schema mode: Uses create_schema() for Voluptuous validation
    - Data mode: Uses loader to convert entity IDs to actual values

    Attributes:
        field_type: Tuple of (device_class, property_type) for the field
        loader: Loader instance (ConstantLoader, SensorLoader, etc.)

    """

    field_type: tuple[str | SensorDeviceClass, str]
    loader: Loader

    def create_schema(self, **_kwargs: Any) -> dict[str, Any]:
        """Create the voluptuous schema for this field type (Schema mode)."""
        return self._get_field_validators(**_kwargs)

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        """Get the field validators for this field type (must be implemented by subclasses)."""
        msg = "Subclasses must implement _get_field_validators"
        raise NotImplementedError(msg)


@dataclass(frozen=True)
class PowerFieldMeta(FieldMeta):
    """Metadata for power value fields."""

    field_type: tuple[Literal[SensorDeviceClass.POWER], Literal["constant"]] = (SensorDeviceClass.POWER, "constant")
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float]())

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "value": vol.All(
                vol.Coerce(float),
                vol.Range(min=0, min_included=True, msg="Value must be positive"),
                NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        min=0,
                        step=0.01,
                        unit_of_measurement=UnitOfPower.KILO_WATT,
                    ),
                ),
            )
        }


@dataclass(frozen=True)
class PowerSensorsFieldMeta(FieldMeta):
    """Metadata for power sensor fields."""

    field_type: tuple[Literal[SensorDeviceClass.POWER], Literal["sensor"]] = (SensorDeviceClass.POWER, "sensor")
    loader: SensorLoader = field(default_factory=lambda: SensorLoader())

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "value": EntitySelector(
                EntitySelectorConfig(domain="sensor", multiple=True, device_class=[SensorDeviceClass.POWER])
            )
        }


@dataclass(frozen=True)
class PowerForecastsFieldMeta(FieldMeta):
    """Metadata for power forecast fields."""

    field_type: tuple[Literal[SensorDeviceClass.POWER], Literal["forecast"]] = (SensorDeviceClass.POWER, "forecast")
    loader: ForecastLoader = field(default_factory=lambda: ForecastLoader())

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "value": EntitySelector(
                EntitySelectorConfig(domain="sensor", multiple=True, device_class=[SensorDeviceClass.POWER])
            )
        }


@dataclass(frozen=True)
class EnergyFieldMeta(FieldMeta):
    """Metadata for energy value fields."""

    field_type: tuple[Literal[SensorDeviceClass.ENERGY], Literal["constant"]] = (SensorDeviceClass.ENERGY, "constant")
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float]())

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "value": vol.All(
                vol.Coerce(float),
                vol.Range(min=0, min_included=True, msg="Value must be positive"),
                NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX, min=0, step=0.01, unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR
                    )
                ),
            )
        }


@dataclass(frozen=True)
class PriceFieldMeta(FieldMeta):
    """Metadata for price value fields."""

    field_type: tuple[Literal[SensorDeviceClass.MONETARY], Literal["constant"]] = (
        SensorDeviceClass.MONETARY,
        "constant",
    )
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float]())

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "value": vol.All(
                vol.Coerce(float),
                NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        step=1,
                        unit_of_measurement=f"{CURRENCY_DOLLAR}/{UnitOfEnergy.KILO_WATT_HOUR}",
                    )
                ),
            )
        }


@dataclass(frozen=True)
class PercentageFieldMeta(FieldMeta):
    """Metadata for percentage value fields."""

    field_type: tuple[Literal["%"], Literal["constant"]] = ("%", "constant")
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float]())

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {"value": vol.All(vol.Coerce(float), vol.Range(min=0, max=100, msg="Value must be between 0 and 100"))}


@dataclass(frozen=True)
class BooleanFieldMeta(FieldMeta):
    """Metadata for boolean value fields."""

    field_type: tuple[Literal["boolean"], Literal["constant"]] = ("boolean", "constant")
    loader: ConstantLoader[bool] = field(default_factory=lambda: ConstantLoader[bool]())

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {"value": BooleanSelector(BooleanSelectorConfig())}


@dataclass(frozen=True)
class ElementNameFieldMeta(FieldMeta):
    """Metadata for element name reference fields."""

    field_type: tuple[Literal["string"], Literal["constant"]] = ("string", "constant")
    loader: ConstantLoader[str] = field(default_factory=lambda: ConstantLoader[str]())

    def _get_field_validators(self, participants: list[str] | None = None, **_kwargs: Any) -> dict[str, Any]:
        # Only show the participants as options in the selector
        participants_list = participants or []
        options: list[SelectOptionDict] = [
            SelectOptionDict(value=participant, label=participant) for participant in participants_list
        ]
        return {
            "value": vol.All(
                str,
                vol.Strip,
                vol.Length(min=1, msg="Element name cannot be empty"),
                SelectSelector(SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)),
            )
        }


@dataclass(frozen=True)
class NameFieldMeta(FieldMeta):
    """Metadata for name value fields."""

    field_type: tuple[Literal["string"], Literal["constant"]] = ("string", "constant")
    loader: ConstantLoader[str] = field(default_factory=lambda: ConstantLoader[str]())

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {"value": vol.All(str, vol.Strip, vol.Length(min=1, msg="Name cannot be empty"))}


@dataclass(frozen=True)
class PowerFlowFieldMeta(FieldMeta):
    """Metadata for power flow value fields."""

    field_type: tuple[Literal[SensorDeviceClass.POWER], Literal["constant"]] = (SensorDeviceClass.POWER, "constant")
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float]())

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "value": vol.All(
                vol.Coerce(float),
                NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX, step=0.01, unit_of_measurement=UnitOfPower.KILO_WATT
                    )
                ),
            )
        }


@dataclass(frozen=True)
class BatterySOCFieldMeta(FieldMeta):
    """Metadata for battery state of charge percentage fields."""

    field_type: tuple[Literal[SensorDeviceClass.BATTERY], Literal["constant"]] = (SensorDeviceClass.BATTERY, "constant")
    loader: ConstantLoader[float] = field(default_factory=lambda: ConstantLoader[float]())

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {"value": vol.All(vol.Coerce(float), vol.Range(min=0, max=100, msg="Value must be between 0 and 100"))}


@dataclass(frozen=True)
class BatterySOCSensorFieldMeta(FieldMeta):
    """Metadata for battery SOC sensor fields."""

    field_type: tuple[Literal[SensorDeviceClass.BATTERY], Literal["sensor"]] = (SensorDeviceClass.BATTERY, "sensor")
    loader: SensorLoader = field(default_factory=lambda: SensorLoader())

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "value": EntitySelector(EntitySelectorConfig(domain="sensor", device_class=[SensorDeviceClass.BATTERY]))
        }


@dataclass(frozen=True)
class EnergySensorsFieldMeta(FieldMeta):
    """Metadata for energy sensor fields."""

    field_type: tuple[Literal[SensorDeviceClass.ENERGY], Literal["sensor"]] = (SensorDeviceClass.ENERGY, "sensor")
    loader: SensorLoader = field(default_factory=lambda: SensorLoader())

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "value": EntitySelector(
                EntitySelectorConfig(
                    domain="sensor",
                    multiple=True,
                    device_class=[SensorDeviceClass.BATTERY, SensorDeviceClass.ENERGY_STORAGE],
                )
            )
        }


@dataclass(frozen=True)
class PriceSensorsFieldMeta(FieldMeta):
    """Metadata for price sensor fields."""

    field_type: tuple[Literal[SensorDeviceClass.MONETARY], Literal["sensor"]] = (SensorDeviceClass.MONETARY, "sensor")
    loader: SensorLoader = field(default_factory=lambda: SensorLoader())

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "value": EntitySelector(
                EntitySelectorConfig(domain="sensor", multiple=True, device_class=[SensorDeviceClass.MONETARY])
            )
        }


@dataclass(frozen=True)
class PriceForecastsFieldMeta(FieldMeta):
    """Metadata for price forecast fields."""

    field_type: tuple[Literal[SensorDeviceClass.MONETARY], Literal["forecast"]] = (
        SensorDeviceClass.MONETARY,
        "forecast",
    )
    loader: ForecastLoader = field(default_factory=lambda: ForecastLoader())

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {"value": EntitySelector(EntitySelectorConfig(domain="sensor", multiple=True))}


@dataclass(frozen=True)
class PricesSensorsAndForecastsFieldMeta(FieldMeta):
    """Metadata for price live and forecast configuration fields."""

    field_type: tuple[Literal[SensorDeviceClass.MONETARY], Literal["live_forecast"]] = (
        SensorDeviceClass.MONETARY,
        "live_forecast",
    )
    loader: ForecastAndSensorLoader = field(default_factory=lambda: ForecastAndSensorLoader())

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "live": EntitySelector(EntitySelectorConfig(domain="sensor", multiple=True)),
            "forecast": EntitySelector(EntitySelectorConfig(domain="sensor", multiple=True)),
        }


# Schema mode type aliases (for configuration with sensor entity IDs)
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

# Data mode type aliases (for runtime with loaded sensor values)
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
