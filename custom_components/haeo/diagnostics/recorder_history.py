"""Recorder history helpers with runtime State validation."""

from datetime import datetime
from typing import Any

from homeassistant.components.recorder import history as recorder_history
from homeassistant.core import HomeAssistant, State


def get_significant_states_full(
    hass: HomeAssistant,
    *,
    start_time: datetime,
    end_time: datetime,
    entity_ids: list[str],
    include_start_time_state: bool = True,
    significant_changes_only: bool = False,
    no_attributes: bool = False,
) -> dict[str, list[State]]:
    """Return significant states as full State objects.

    Home Assistant stubs type this as ``State | dict`` when minimal_response may be true.
    This helper always requests full states (``no_attributes=False`` by default) and
    keeps only values that are ``State`` instances at runtime.
    """
    raw = recorder_history.get_significant_states(
        hass,
        start_time=start_time,
        end_time=end_time,
        entity_ids=entity_ids,
        include_start_time_state=include_start_time_state,
        significant_changes_only=significant_changes_only,
        no_attributes=no_attributes,
    )
    return _states_only_history(raw)


def _states_only_history(
    result: dict[str, list[State | dict[str, Any]]],
) -> dict[str, list[State]]:
    """Drop minimal-response dict entries; keep full State objects only."""
    narrowed: dict[str, list[State]] = {}
    for entity_id, states in result.items():
        full_states = [state for state in states if isinstance(state, State)]
        if full_states:
            narrowed[entity_id] = full_states
    return narrowed
