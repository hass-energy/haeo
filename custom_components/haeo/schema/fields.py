"""Field types for HAEO type system using Annotated types."""

from __future__ import annotations

from abc import ABC
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import UnitOfPower
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol


@dataclass(frozen=True)
class FieldMeta(ABC):
    """Base class for field metadata."""

    field_type: tuple[str | SensorDeviceClass, str]

    def create_schema(self, **_kwargs: Any) -> dict[str, Any]:
        """Create the voluptuous schema for this field type."""
        return self._get_field_validators(**_kwargs)

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        """Get the field key name for this field type."""
        msg = "Subclasses must implement _get_field_validators"
        raise NotImplementedError(msg)


@dataclass(frozen=True)
class PowerFieldMeta(FieldMeta):
    """Metadata for power value fields."""

    field_type: tuple[Literal[SensorDeviceClass.POWER], Literal["constant"]] = (SensorDeviceClass.POWER, "constant")

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "value": vol.All(
                vol.Coerce(float),
                vol.Range(min=0, min_included=True, msg="Value must be positive"),
                NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        min=1,
                        step=1,
                        unit_of_measurement=UnitOfPower.WATT,
                    ),
                ),
            )
        }


@dataclass(frozen=True)
class PowerSensorsFieldMeta(FieldMeta):
    """Metadata for power sensor fields."""

    field_type: tuple[Literal[SensorDeviceClass.POWER], Literal["sensor"]] = (SensorDeviceClass.POWER, "sensor")

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

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "value": vol.All(
                vol.Coerce(float),
                vol.Range(min=0, min_included=True, msg="Value must be positive"),
                NumberSelector(
                    NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, step=1, unit_of_measurement="Wh")
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

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "value": vol.All(
                vol.Coerce(float),
                NumberSelector(NumberSelectorConfig(mode=NumberSelectorMode.BOX, step=1, unit_of_measurement="$/kWh")),
            )
        }


@dataclass(frozen=True)
class PercentageFieldMeta(FieldMeta):
    """Metadata for percentage value fields."""

    field_type: tuple[Literal["%"], Literal["constant"]] = ("%", "constant")

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {"value": vol.All(vol.Coerce(float), vol.Range(min=0, max=100, msg="Value must be between 0 and 100"))}


@dataclass(frozen=True)
class BooleanFieldMeta(FieldMeta):
    """Metadata for boolean value fields."""

    field_type: tuple[Literal["boolean"], Literal["constant"]] = ("boolean", "constant")

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {"value": BooleanSelector(BooleanSelectorConfig())}


@dataclass(frozen=True)
class ElementNameFieldMeta(FieldMeta):
    """Metadata for element name reference fields."""

    field_type: tuple[Literal["string"], Literal["constant"]] = ("string", "constant")

    def _get_field_validators(self, participants: Sequence[str], **_kwargs: Any) -> dict[str, Any]:
        # Only show the participants as options in the selector
        options = [{"value": participant, "label": participant} for participant in participants]
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

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {"value": vol.All(str, vol.Strip, vol.Length(min=1, msg="Name cannot be empty"))}


@dataclass(frozen=True)
class PowerFlowFieldMeta(FieldMeta):
    """Metadata for power flow value fields."""

    field_type: tuple[Literal[SensorDeviceClass.POWER], Literal["constant"]] = (SensorDeviceClass.POWER, "constant")

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "value": vol.All(
                vol.Coerce(float),
                NumberSelector(
                    NumberSelectorConfig(mode=NumberSelectorMode.BOX, step=1, unit_of_measurement=UnitOfPower.WATT)
                ),
            )
        }


@dataclass(frozen=True)
class BatterySOCFieldMeta(FieldMeta):
    """Metadata for battery state of charge percentage fields."""

    field_type: tuple[Literal[SensorDeviceClass.BATTERY], Literal["constant"]] = (SensorDeviceClass.BATTERY, "constant")

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {"value": vol.All(vol.Coerce(float), vol.Range(min=0, max=100, msg="Value must be between 0 and 100"))}


@dataclass(frozen=True)
class BatterySOCSensorFieldMeta(FieldMeta):
    """Metadata for battery SOC sensor fields."""

    field_type: tuple[Literal[SensorDeviceClass.BATTERY], Literal["sensor"]] = (SensorDeviceClass.BATTERY, "sensor")

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "value": EntitySelector(EntitySelectorConfig(domain="sensor", device_class=[SensorDeviceClass.BATTERY]))
        }


@dataclass(frozen=True)
class EnergySensorsFieldMeta(FieldMeta):
    """Metadata for energy sensor fields."""

    field_type: tuple[Literal[SensorDeviceClass.ENERGY], Literal["sensor"]] = (SensorDeviceClass.ENERGY, "sensor")

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

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {"value": EntitySelector(EntitySelectorConfig(domain="sensor", multiple=True))}


@dataclass(frozen=True)
class PricesSensorsAndForecastsFieldMeta(FieldMeta):
    """Metadata for price live and forecast configuration fields."""

    field_type: tuple[Literal[SensorDeviceClass.MONETARY], Literal["live_forecast"]] = (
        SensorDeviceClass.MONETARY,
        "live_forecast",
    )

    def _get_field_validators(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "live": EntitySelector(EntitySelectorConfig(domain="sensor", multiple=True)),
            "forecast": EntitySelector(EntitySelectorConfig(domain="sensor", multiple=True)),
        }


PowerField = Annotated[float, PowerFieldMeta()]
PowerSensorsField = Annotated[Sequence[str], PowerSensorsFieldMeta()]
PowerForecastsField = Annotated[Sequence[str], PowerForecastsFieldMeta()]

PowerFlowField = Annotated[float, PowerFlowFieldMeta()]

EnergyField = Annotated[float, EnergyFieldMeta()]
EnergySensorsField = Annotated[Sequence[str], EnergySensorsFieldMeta()]

PercentageField = Annotated[float, PercentageFieldMeta()]
BooleanField = Annotated[bool, BooleanFieldMeta()]

ElementNameField = Annotated[str, ElementNameFieldMeta()]
NameField = Annotated[str, NameFieldMeta()]

BatterySOCField = Annotated[float, BatterySOCFieldMeta()]
BatterySOCSensorField = Annotated[str, BatterySOCSensorFieldMeta()]

PriceField = Annotated[float, PriceFieldMeta()]
PriceSensorsField = Annotated[Sequence[str], PriceSensorsFieldMeta()]
PriceForecastsField = Annotated[Sequence[str], PriceForecastsFieldMeta()]
PricesSensorsAndForecastsField = Annotated[
    dict[Literal["live", "forecast"], Sequence[str]], PricesSensorsAndForecastsFieldMeta()
]
