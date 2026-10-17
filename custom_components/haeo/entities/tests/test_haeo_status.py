"""Tests for the optimization status sensor."""

from datetime import UTC, datetime
from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.helpers.device_registry import DeviceEntry
import pytest

from custom_components.haeo.const import ELEMENT_TYPE_NETWORK, OUTPUT_NAME_OPTIMIZATION_STATUS
from custom_components.haeo.entities.haeo_status import HaeoStatusSensor

COMPLETED_AT = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
TOPOLOGY = {"nodes": [], "edges": [], "groups": {}}


def _status_sensor(*, status: str, data: object, error: str | None) -> HaeoStatusSensor:
    coordinator = Mock()
    coordinator.optimization_status = status
    coordinator.data = data
    coordinator.optimization_error = error
    coordinator.topology = TOPOLOGY
    network = ConfigSubentry(
        data=MappingProxyType({}), subentry_type=ELEMENT_TYPE_NETWORK, title="System", unique_id=None
    )
    sensor = HaeoStatusSensor(
        coordinator, device_entry=Mock(spec=DeviceEntry), network_subentry=network, unique_id="id"
    )
    sensor.async_write_ha_state = Mock()
    sensor._handle_coordinator_update()
    return sensor


@pytest.mark.parametrize(
    ("status", "data", "error", "expected_extra"),
    [
        pytest.param("pending", None, None, {}, id="pending"),
        pytest.param(
            "success",
            Mock(completed_at=COMPLETED_AT),
            None,
            {"last_run": "2024-01-01T12:00:00+00:00"},
            id="success",
        ),
        pytest.param(
            "failed",
            Mock(completed_at=COMPLETED_AT),
            "Unbounded",
            {"last_run": "2024-01-01T12:00:00+00:00", "error": "Unbounded"},
            id="failed_after_a_success",
        ),
        pytest.param("failed", None, "Unbounded", {"error": "Unbounded"}, id="failed_first_run"),
    ],
)
def test_status_sensor_reports_optimization_status(
    status: str, data: object, error: str | None, expected_extra: dict[str, str]
) -> None:
    """The sensor stays available and shows the status, the last successful run, and any error."""
    sensor = _status_sensor(status=status, data=data, error=error)

    assert sensor.available
    assert sensor.native_value == status
    assert sensor.options == ["failed", "pending", "success"]
    assert sensor.extra_state_attributes == {
        "element_name": "System",
        "element_type": ELEMENT_TYPE_NETWORK,
        "output_name": OUTPUT_NAME_OPTIMIZATION_STATUS,
        "field_type": "status",
        "source_role": "output",
        "advanced": False,
        "topology": TOPOLOGY,
        **expected_extra,
    }
