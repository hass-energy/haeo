"""Coordinator and output builders shared by the sensor platform and sensor entity tests."""

from datetime import UTC, datetime

# Coordinator output fixtures use runtime string keys that cannot satisfy the
# Literal key types of SubentryDevices.
from typing import Any, Literal  # noqa: TID251
from unittest.mock import Mock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.util import dt as dt_util

from custom_components.haeo.coordinator import CoordinatorData, CoordinatorOutput, ForecastPoint, OptimizationContext
from custom_components.haeo.core.data.loader.extractors.haeo import InterpolationMode
from custom_components.haeo.core.model import OutputType


def make_coordinator_data(
    outputs: dict[str, Any] | None = None,
    *,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> CoordinatorData | None:
    """Create a CoordinatorData instance for tests.

    Args:
        outputs: Dict of outputs. If None, returns None to simulate no data.
        started_at: Optimization start time; defaults to current UTC time.
        completed_at: Optimization completion time; defaults to current UTC time.

    Returns:
        CoordinatorData with the given outputs, or None.

    """
    if outputs is None:
        return None
    context = OptimizationContext(
        hub_config={},
        horizon_start=datetime.fromtimestamp(1000.0, tz=dt_util.UTC),
        participants={},
        source_states={},
    )
    run_started_at = started_at or datetime.now(UTC)
    run_completed_at = completed_at or datetime.now(UTC)
    return CoordinatorData(
        context=context,
        outputs=outputs,
        started_at=run_started_at,
        completed_at=run_completed_at,
    )


def create_mock_coordinator() -> Mock:
    """Create a mock coordinator for sensor tests.

    Returns a Mock configured with the minimal interface needed for sensor tests.
    Callers can use this where HaeoDataUpdateCoordinator is expected since Mock
    attribute access returns Any, making it compatible at runtime.
    """
    coordinator = Mock()
    coordinator.data = make_coordinator_data({})
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    return coordinator


def make_output(
    *,
    type_: OutputType,
    unit: str | None,
    state: float | str | None,
    forecast: list[ForecastPoint] | None,
    entity_category: EntityCategory | None,
    device_class: SensorDeviceClass | None,
    state_class: SensorStateClass | None,
    options: tuple[str, ...] | None,
    direction: Literal["+", "-"] | None = None,
    interpolation_mode: InterpolationMode | None = None,
) -> CoordinatorOutput:
    """Create a coordinator output with every display field given explicitly."""
    return CoordinatorOutput(
        type=type_,
        unit=unit,
        state=state,
        forecast=forecast,
        interpolation_mode=interpolation_mode,
        entity_category=entity_category,
        device_class=device_class,
        state_class=state_class,
        options=options,
        direction=direction,
    )
