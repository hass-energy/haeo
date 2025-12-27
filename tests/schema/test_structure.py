"""Tests for schema utilities covering loader dispatch."""

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Annotated, Any, TypedDict, cast

from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.data.loader import ConstantLoader
from custom_components.haeo.elements import ElementConfigSchema
from custom_components.haeo.schema import available as schema_available
from custom_components.haeo.schema import compose_field, get_loader_instance
from custom_components.haeo.schema import load as schema_load
from custom_components.haeo.schema.fields import Constant, Default, LoaderMeta, PositiveKW


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
class TrackingLoaderMeta(LoaderMeta):
    """LoaderMeta wrapper for testing with TrackingLoader instances."""

    tracking_loader: TrackingLoader


def test_compose_field_extracts_all_metadata() -> None:
    """compose_field() extracts Validator, LoaderMeta, and Default from Annotated."""
    field_type = Annotated[float, PositiveKW(), Constant(float), Default(value=5.0)]
    spec = compose_field(field_type)

    assert isinstance(spec.validator, PositiveKW)
    assert isinstance(spec.loader, Constant)
    assert spec.default is not None
    assert spec.default.value == 5.0


def test_compose_field_handles_missing_metadata() -> None:
    """compose_field() returns None for missing metadata components."""
    # Type with only validator
    field_type = Annotated[float, PositiveKW()]
    spec = compose_field(field_type)

    assert isinstance(spec.validator, PositiveKW)
    assert spec.loader is None
    assert spec.default is None


@pytest.mark.parametrize("available_result", [True, False])
def test_schema_available_delegates_to_loader(
    monkeypatch: pytest.MonkeyPatch,
    *,
    available_result: bool,
) -> None:
    """available() defers availability checks to the underlying loader."""

    loader = TrackingLoader(available_result=available_result, loaded_value=42)

    # Mock the get_loader_instance to return our tracking loader
    def mock_get_loader(_field_name: str, _config_class: type) -> TrackingLoader:
        return loader

    monkeypatch.setattr("custom_components.haeo.schema.get_loader_instance", mock_get_loader)

    class ConfigData(TypedDict):
        value: Annotated[int, PositiveKW(), Constant(int)]

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

    # Mock the get_loader_instance to return our tracking loader only for "value" field
    original_get_loader = get_loader_instance

    def mock_get_loader(field_name: str, config_class: type) -> ConstantLoader[int]:
        if field_name == "value":
            return loader  # type: ignore[return-value]
        return cast("ConstantLoader[int]", original_get_loader(field_name, config_class))

    monkeypatch.setattr("custom_components.haeo.schema.get_loader_instance", mock_get_loader)

    class ConfigData(TypedDict):
        element_type: str
        value: Annotated[int, PositiveKW(), Constant(int)]

    entry = SimpleNamespace(data=ConfigData)
    monkeypatch.setattr("custom_components.haeo.schema._get_registry_entry", lambda _element: entry)

    config = cast("ElementConfigSchema", {"element_type": "stub", "value": 123})
    hass = cast("HomeAssistant", object())

    result = await schema_load(config, hass, forecast_times=[])

    assert result.get("value") == 99
    assert len(loader.load_calls) == 1


def test_get_loader_instance_returns_correct_loader_for_constant() -> None:
    """get_loader_instance returns ConstantLoader for Constant fields."""

    class ConfigData(TypedDict):
        power: Annotated[float, PositiveKW(), Constant(float)]

    loader = get_loader_instance("power", ConfigData)
    assert isinstance(loader, ConstantLoader)


def test_get_loader_instance_returns_default_for_missing_field() -> None:
    """get_loader_instance returns default loader for missing fields."""

    class ConfigData(TypedDict):
        pass

    loader = get_loader_instance("nonexistent", ConfigData)
    assert isinstance(loader, ConstantLoader)
