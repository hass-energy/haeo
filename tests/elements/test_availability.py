"""Tests for elements availability helpers."""

from typing import Any

from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.elements.availability import schema_config_available
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value


def test_schema_config_available_allows_constants_and_none(hass: HomeAssistant) -> None:
    """schema_config_available ignores constant, none, and connection targets."""
    config: dict[str, Any] = {
        "constant": as_constant_value(1.0),
        "none": as_none_value(),
        "connection": as_connection_target("bus"),
        "nested": {"value": None},
    }

    assert schema_config_available(config, hass=hass) is True


def test_schema_config_available_returns_false_for_unavailable_entity(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """schema_config_available returns False when entity values are unavailable."""

    def _fake_available(self: TimeSeriesLoader, *, hass: HomeAssistant, value: Any) -> bool:  # noqa: ARG001
        return False

    monkeypatch.setattr(TimeSeriesLoader, "available", _fake_available)

    config = {"sensor": as_entity_value(["sensor.test"])}

    assert schema_config_available(config, hass=hass) is False


def test_schema_config_available_handles_nested_entity(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """schema_config_available returns True for nested entity values when available."""
    calls: list[Any] = []

    def _fake_available(self: TimeSeriesLoader, *, hass: HomeAssistant, value: Any) -> bool:  # noqa: ARG001
        calls.append(value)
        return True

    monkeypatch.setattr(TimeSeriesLoader, "available", _fake_available)

    config = {"nested": {"sensor": as_entity_value(["sensor.test"])} }

    assert schema_config_available(config, hass=hass) is True
    assert calls
