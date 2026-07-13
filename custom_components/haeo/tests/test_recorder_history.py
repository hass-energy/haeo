"""Tests for the recorder history helpers."""

from datetime import UTC, datetime
from unittest.mock import patch

from homeassistant.core import HomeAssistant, State

from custom_components.haeo.diagnostics.recorder_history import get_significant_states_full


async def test_get_significant_states_full_keeps_only_state_objects(hass: HomeAssistant) -> None:
    """Minimal-response dict entries are dropped; full State objects are kept."""
    start = datetime(2026, 1, 20, 14, 0, 0, tzinfo=UTC)
    end = datetime(2026, 1, 20, 15, 0, 0, tzinfo=UTC)

    full_state = State("sensor.full", "50", {"unit_of_measurement": "%"})
    raw: dict[str, list[State | dict[str, object]]] = {
        "sensor.full": [full_state, {"state": "51", "last_changed": "2026-01-20T14:30:00+00:00"}],
        "sensor.minimal_only": [{"state": "1"}],
        "sensor.empty": [],
    }

    with patch(
        "custom_components.haeo.diagnostics.recorder_history.recorder_history.get_significant_states",
        return_value=raw,
    ) as mock_get_states:
        result = get_significant_states_full(
            hass,
            start_time=start,
            end_time=end,
            entity_ids=["sensor.full", "sensor.minimal_only", "sensor.empty"],
        )

    mock_get_states.assert_called_once_with(
        hass,
        start_time=start,
        end_time=end,
        entity_ids=["sensor.full", "sensor.minimal_only", "sensor.empty"],
        include_start_time_state=True,
        significant_changes_only=False,
        no_attributes=False,
    )

    # Entities with no full State objects are omitted entirely.
    assert result == {"sensor.full": [full_state]}
