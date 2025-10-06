"""Test scenario1: Basic battery and grid optimization scenario with solar generation and constant load."""

from collections.abc import Sequence
from typing import Any
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN


async def test_scenario1_setup_and_optimization(
    hass: HomeAssistant, scenario_config: dict[str, Any], scenario_states: Sequence[dict[str, Any]]
) -> None:
    """Test that scenario1 sets up correctly and optimization succeeds."""

    # Set up sensor states from scenario data
    for state_data in scenario_states:
        entity_id = state_data["entity_id"]
        state_value = state_data["state"]
        attributes = state_data.get("attributes", {})
        hass.states.async_set(entity_id, state_value, attributes)

    # Create mock config entry - pass config directly since keys match constants
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=scenario_config,
    )

    # Set up the integration using proper integration setup pattern
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify optimization succeeded (scenario should work properly)
    optimization_status = hass.states.get("sensor.haeo_optimization_status")
    assert optimization_status is not None
    assert optimization_status.state == "success"

    # Verify cost and duration sensors have valid values
    optimization_cost = hass.states.get("sensor.haeo_optimization_cost")
    optimization_duration = hass.states.get("sensor.haeo_optimization_duration")

    assert optimization_cost is not None
    cost_state = optimization_cost.state
    assert cost_state not in ["unknown", "unavailable", None]
    cost_value = float(cost_state)
    assert isinstance(cost_value, (int, float))

    assert optimization_duration is not None
    duration_state = optimization_duration.state
    assert duration_state not in ["unknown", "unavailable", None]
    duration_value = float(duration_state)
    assert isinstance(duration_value, (int, float))
    assert duration_value > 0

    # For 288 periods (24h x 5min), optimization should be reasonably fast (< 5 seconds)
    assert duration_value < 5.0, f"Optimization took {duration_value}s, expected < 5s"
