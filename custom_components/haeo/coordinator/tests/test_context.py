"""Tests for the optimization context the coordinator captures."""

from datetime import datetime
from unittest.mock import MagicMock

from homeassistant.core import State
from homeassistant.util import dt as dt_util
import pytest

from custom_components.haeo.coordinator import OptimizationContext, build_optimization_context


def test_build_optimization_context_collects_source_states() -> None:
    """build_optimization_context collects source states from all input stores."""
    mock_state1 = State("sensor.power1", "100")
    mock_state2 = State("sensor.power2", "200")

    mock_store1 = MagicMock()
    mock_store1.captured_source_states = {"sensor.power1": mock_state1}

    mock_store2 = MagicMock()
    mock_store2.captured_source_states = {"sensor.power2": mock_state2}

    input_stores = {
        ("Battery", ("basic", "power")): mock_store1,
        ("Solar", ("basic", "forecast")): mock_store2,
    }

    mock_horizon = MagicMock()
    mock_horizon.current_start_time = datetime.fromtimestamp(1000.0, tz=dt_util.UTC)

    participant_configs: dict[str, dict[str, object]] = {
        "Battery": {"element_type": "battery", "basic": {"capacity": 10.0}},
        "Solar": {"element_type": "solar", "basic": {"forecast": "sensor.solar"}},
    }

    context = build_optimization_context(
        hub_config={},
        # Fixture configs omit required ElementConfigSchema keys; only source_states collection is under test.
        participant_configs=participant_configs,  # type: ignore[arg-type]
        input_stores=input_stores,
        horizon_manager=mock_horizon,
    )

    assert "sensor.power1" in context.source_states
    assert "sensor.power2" in context.source_states
    assert context.source_states["sensor.power1"] == mock_state1
    assert context.source_states["sensor.power2"] == mock_state2


def test_build_optimization_context_captures_horizon_start() -> None:
    """build_optimization_context captures horizon start time as datetime."""
    mock_horizon = MagicMock()
    expected_time = datetime.fromtimestamp(1000.0, tz=dt_util.UTC)
    mock_horizon.current_start_time = expected_time

    context = build_optimization_context(
        hub_config={},
        participant_configs={},
        input_stores={},
        horizon_manager=mock_horizon,
    )

    assert context.horizon_start == expected_time


def test_build_optimization_context_falls_back_to_utcnow_when_no_start_time() -> None:
    """build_optimization_context uses datetime.now(UTC) when horizon has no start time."""
    mock_horizon = MagicMock()
    mock_horizon.current_start_time = None

    context = build_optimization_context(
        hub_config={},
        participant_configs={},
        input_stores={},
        horizon_manager=mock_horizon,
    )

    assert context.horizon_start is not None
    assert isinstance(context.horizon_start, datetime)


def test_optimization_context_is_immutable() -> None:
    """OptimizationContext is frozen and cannot be modified."""
    context = OptimizationContext(
        hub_config={},
        horizon_start=datetime.fromtimestamp(1000.0, tz=dt_util.UTC),
        participants={},
        source_states={},
    )

    with pytest.raises(AttributeError):
        context.participants = {}  # type: ignore[misc]

    with pytest.raises(AttributeError):
        context.source_states = {}  # type: ignore[misc]

    with pytest.raises(AttributeError):
        context.horizon_start = datetime.fromtimestamp(2000.0, tz=dt_util.UTC)  # type: ignore[misc]
