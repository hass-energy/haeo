"""Tests for schema utilities covering loader dispatch."""

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Annotated, Any, NotRequired, TypedDict, cast

from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.data.loader import ConstantLoader
from custom_components.haeo.elements import ElementConfigSchema
from custom_components.haeo.schema import available as schema_available
from custom_components.haeo.schema import get_loader_instance
from custom_components.haeo.schema import load as schema_load
from custom_components.haeo.schema.fields import FieldMeta


class TrackingLoader(ConstantLoader[int]):
    """Constant loader variant recording interactions for assertions."""

    def __init__(self, *, available_result: bool, loaded_value: int) -> None:
        """Store expected results and tracking state."""
        super().__init__(int)
        self.available_result = available_result
        self.loaded_value = loaded_value
        self.available_calls: list[dict[str, Any]] = []
        self.load_calls: list[dict[str, Any]] = []

    def available(self, value: Any, **kwargs: Any) -> bool:
        """Record the availability check before returning the configured result."""
        self.available_calls.append({"value": value, **kwargs})
        return self.available_result

    async def load(self, *, value: Any, **kwargs: Any) -> int:
        """Record the load request and return the configured value."""
        self.load_calls.append({"value": value, **kwargs})
        return self.loaded_value


@dataclass(frozen=True)
class TrackingFieldMeta(FieldMeta):
    """FieldMeta wrapper for TrackingLoader instances."""

    loader: TrackingLoader

    def _get_field_validators(self, **_kwargs: Any) -> Any:
        return lambda value: value


@pytest.mark.parametrize("available_result", [True, False])
def test_schema_available_delegates_to_loader(
    monkeypatch: pytest.MonkeyPatch,
    *,
    available_result: bool,
) -> None:
    """available() defers availability checks to the underlying loader."""

    loader = TrackingLoader(available_result=available_result, loaded_value=42)

    class ConfigData(TypedDict):
        value: Annotated[int, TrackingFieldMeta(field_type="constant", loader=loader)]

    entry = SimpleNamespace(data=ConfigData)
    monkeypatch.setattr("custom_components.haeo.schema._get_registry_entry", lambda _element: entry)

    config = cast("ElementConfigSchema", {"element_type": "stub", "value": "sensor.example"})
    hass = cast("HomeAssistant", object())

    result = schema_available(config, hass=hass)

    assert result is available_result
    assert loader.available_calls == [{"value": "sensor.example", "hass": hass}]


async def test_schema_load_calls_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    """load() uses loader instances to fetch runtime values."""

    loader = TrackingLoader(available_result=True, loaded_value=99)

    class ConfigData(TypedDict):
        value: Annotated[int, TrackingFieldMeta(field_type="constant", loader=loader)]

    entry = SimpleNamespace(data=ConfigData)
    monkeypatch.setattr("custom_components.haeo.schema._get_registry_entry", lambda _element: entry)

    config = cast("ElementConfigSchema", {"element_type": "stub", "value": "sensor.example"})
    hass = cast("HomeAssistant", object())

    loaded = cast("ConfigData", await schema_load(config, hass=hass, forecast_times=[]))

    assert loaded["value"] == 99
    assert loader.load_calls == [{"value": "sensor.example", "hass": hass, "forecast_times": []}]


def test_get_loader_instance_fallback() -> None:
    """get_loader_instance falls back to a ConstantLoader when metadata is missing."""

    class PlainConfig(TypedDict):
        value: int

    loader = get_loader_instance("value", PlainConfig)
    assert isinstance(loader, ConstantLoader)


async def test_optional_none_values_are_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Optional fields provided as None should not trigger loader access."""

    required_loader = TrackingLoader(available_result=True, loaded_value=11)
    optional_loader = TrackingLoader(available_result=True, loaded_value=99)

    class ConfigData(TypedDict):
        value: Annotated[int, TrackingFieldMeta(field_type="constant", loader=required_loader)]
        optional: NotRequired[Annotated[int | None, TrackingFieldMeta(field_type="constant", loader=optional_loader)]]

    entry = SimpleNamespace(data=ConfigData)
    monkeypatch.setattr("custom_components.haeo.schema._get_registry_entry", lambda _element: entry)

    config = cast(
        "ElementConfigSchema",
        {"element_type": "stub", "value": "sensor.example", "optional": None},
    )
    hass = cast("HomeAssistant", object())

    assert schema_available(config, hass=hass) is True
    assert optional_loader.available_calls == []

    loaded = cast("ConfigData", await schema_load(config, hass=hass, forecast_times=[]))
    assert "optional" not in loaded
    assert required_loader.load_calls == [{"value": "sensor.example", "hass": hass, "forecast_times": []}]
    assert optional_loader.load_calls == []
