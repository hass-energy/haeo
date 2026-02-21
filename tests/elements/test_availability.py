"""Tests for elements availability helpers."""

from typing import Any

import pytest

from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.elements.availability import schema_config_available
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from tests.conftest import FakeStateMachine


def test_schema_config_available_allows_constants_and_none() -> None:
    """schema_config_available ignores constant, none, and connection targets."""
    config: dict[str, Any] = {
        "constant": as_constant_value(1.0),
        "none": as_none_value(),
        "connection": as_connection_target("bus"),
        "nested": {"value": None},
    }

    assert schema_config_available(config, sm=FakeStateMachine({})) is True


def test_schema_config_available_returns_false_for_unavailable_entity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """schema_config_available returns False when entity values are unavailable."""

    def _fake_available(self: TimeSeriesLoader, *, sm: FakeStateMachine, value: Any) -> bool:  # noqa: ARG001
        return False

    monkeypatch.setattr(TimeSeriesLoader, "available", _fake_available)

    config = {"sensor": as_entity_value(["sensor.test"])}

    assert schema_config_available(config, sm=FakeStateMachine({})) is False


def test_schema_config_available_handles_nested_entity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """schema_config_available returns True for nested entity values when available."""
    calls: list[Any] = []

    def _fake_available(self: TimeSeriesLoader, *, sm: FakeStateMachine, value: Any) -> bool:  # noqa: ARG001
        calls.append(value)
        return True

    monkeypatch.setattr(TimeSeriesLoader, "available", _fake_available)

    config = {"nested": {"sensor": as_entity_value(["sensor.test"])}}

    assert schema_config_available(config, sm=FakeStateMachine({})) is True
    assert calls
