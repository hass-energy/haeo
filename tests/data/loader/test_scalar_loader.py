"""Tests for ScalarLoader handling current sensor values."""

from typing import cast

import pytest

from custom_components.haeo.core.schema import EntityValue, as_entity_value
from custom_components.haeo.data.loader.scalar_loader import ScalarLoader
from tests.conftest import FakeEntityState, FakeStateMachine


async def test_scalar_loader_available_missing_sensor() -> None:
    """Scalar loader is unavailable when sensors are missing."""
    loader = ScalarLoader()
    assert loader.available(sm=FakeStateMachine({}), value=as_entity_value(["sensor.missing"])) is False


async def test_scalar_loader_available_empty_list() -> None:
    """Scalar loader is unavailable when no sensors are provided."""
    loader = ScalarLoader()

    assert loader.available(sm=FakeStateMachine({}), value=as_entity_value([])) is False


async def test_scalar_loader_available_invalid_entity_value() -> None:
    """Scalar loader is unavailable for invalid entity value types."""
    loader = ScalarLoader()
    value = cast("EntityValue", {"type": "entity", "value": 123})

    assert loader.available(sm=FakeStateMachine({}), value=value) is False


async def test_scalar_loader_available_false_for_non_numeric_state() -> None:
    """Scalar loader reports unavailable for non-numeric state values."""
    loader = ScalarLoader()
    sm = FakeStateMachine(
        {
            "sensor.bad_state": FakeEntityState(
                entity_id="sensor.bad_state",
                state="unknown",
                attributes={},
            )
        }
    )
    assert loader.available(sm=sm, value=as_entity_value(["sensor.bad_state"])) is False


async def test_scalar_loader_load_requires_entity_ids() -> None:
    """Scalar loader raises when no sensors are provided."""
    loader = ScalarLoader()
    with pytest.raises(ValueError, match="At least one sensor entity is required"):
        await loader.load(sm=FakeStateMachine({}), value=as_entity_value([]))


async def test_scalar_loader_load_raises_when_sensor_missing() -> None:
    """Scalar loader raises when a sensor entity is missing."""
    loader = ScalarLoader()
    with pytest.raises(ValueError, match=r"Sensor sensor\.missing not found or unavailable"):
        await loader.load(sm=FakeStateMachine({}), value=as_entity_value(["sensor.missing"]))


async def test_scalar_loader_load_raises_for_non_numeric_state() -> None:
    """Scalar loader raises when sensor state is not numeric."""
    loader = ScalarLoader()
    sm = FakeStateMachine(
        {
            "sensor.bad_state": FakeEntityState(
                entity_id="sensor.bad_state",
                state="unknown",
                attributes={},
            )
        }
    )

    with pytest.raises(ValueError, match=r"Sensor sensor\.bad_state has no numeric state"):
        await loader.load(sm=sm, value=as_entity_value(["sensor.bad_state"]))


async def test_scalar_loader_load_raises_for_invalid_entity_value() -> None:
    """Scalar loader raises when entity value is invalid."""
    loader = ScalarLoader()
    value = cast("EntityValue", {"type": "entity", "value": 123})

    with pytest.raises(TypeError, match="sensor entity ID"):
        await loader.load(sm=FakeStateMachine({}), value=value)


async def test_scalar_loader_loads_and_converts_units() -> None:
    """Scalar loader converts units and sums multiple sensors."""
    loader = ScalarLoader()

    sm = FakeStateMachine(
        {
            "sensor.power_one": FakeEntityState(
                entity_id="sensor.power_one",
                state="500",
                attributes={"device_class": "power", "unit_of_measurement": "W"},
            ),
            "sensor.power_two": FakeEntityState(
                entity_id="sensor.power_two",
                state="1.5",
                attributes={"device_class": "power", "unit_of_measurement": "kW"},
            ),
        }
    )

    assert loader.available(sm=sm, value=as_entity_value(["sensor.power_one", "sensor.power_two"])) is True

    result = await loader.load(sm=sm, value=as_entity_value(["sensor.power_one", "sensor.power_two"]))

    assert result == pytest.approx(2.0)


async def test_scalar_loader_handles_invalid_device_class() -> None:
    """Scalar loader accepts numeric values with unknown device classes."""
    loader = ScalarLoader()

    sm = FakeStateMachine(
        {
            "sensor.unknown_class": FakeEntityState(
                entity_id="sensor.unknown_class",
                state="2.5",
                attributes={"device_class": "not-a-class", "unit_of_measurement": "kW"},
            )
        }
    )

    assert loader.available(sm=sm, value=as_entity_value(["sensor.unknown_class"])) is True

    result = await loader.load(sm=sm, value=as_entity_value(["sensor.unknown_class"]))

    assert result == pytest.approx(2.5)
