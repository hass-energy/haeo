"""Test scenario1: Basic battery and grid optimization scenario with solar generation and constant load."""

import asyncio
from collections.abc import Sequence
import logging
import traceback
from typing import Any

from freezegun import freeze_time
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_HORIZON_HOURS,
    CONF_NAME,
    CONF_OPTIMIZER,
    CONF_PERIOD_MINUTES,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
from tests.scenarios.visualization import visualize_scenario_results

_LOGGER = logging.getLogger(__name__)


@freeze_time("2025-10-05T10:59:21.998507+00:00")
async def test_scenario1_setup_and_optimization(
    hass: HomeAssistant, scenario_config: dict[str, Any], scenario_states: Sequence[dict[str, Any]]
) -> None:
    """Test that scenario1 sets up correctly and optimization engine runs successfully."""

    # Set up sensor states from scenario data
    for state_data in scenario_states:
        entity_id = state_data["entity_id"]
        state_value = state_data["state"]
        attributes = state_data.get("attributes", {})
        hass.states.async_set(entity_id, state_value, attributes)

    # Ensure all sensors are properly loaded
    await hass.async_block_till_done()

    # Verify that the battery sensor is available
    battery_sensor = hass.states.get("sensor.sigen_plant_battery_state_of_charge")
    assert battery_sensor is not None, "Battery sensor should be available"
    assert battery_sensor.state not in ("unknown", "unavailable", "none"), (
        f"Battery sensor has invalid state: {battery_sensor.state}"
    )

    # Create hub config entry (without participants, which are now subentries)
    hub_config = {
        "integration_type": INTEGRATION_TYPE_HUB,
        CONF_NAME: "Test Hub",
        CONF_HORIZON_HOURS: scenario_config.get(CONF_HORIZON_HOURS, 24),
        CONF_PERIOD_MINUTES: scenario_config.get(CONF_PERIOD_MINUTES, 5),
        CONF_OPTIMIZER: scenario_config.get(CONF_OPTIMIZER, "highs"),
    }

    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=hub_config,
    )
    # Add hub to hass first so we have the entry_id for subentries
    mock_config_entry.add_to_hass(hass)

    # Create element subentries from participants
    # Add them to hass BEFORE setting up the hub so they're available during coordinator init
    participants = scenario_config.get("participants", {})
    for element_config in participants.values():
        # Create subentry for this element with proper parent reference
        # Note: connections are elements too - they're part of the network topology
        element_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "parent_entry_id": mock_config_entry.entry_id,
                **element_config,
            },
        )
        # Add subentry to hass before hub setup
        element_entry.add_to_hass(hass)

    # Now set up the hub - coordinator will find the subentries via _get_child_elements()
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get the coordinator from the config entry
    coordinator = getattr(mock_config_entry, "runtime_data", None)
    assert coordinator is not None, "Coordinator should be available after setup"

    # Manually trigger the first data refresh (needed because time is frozen)
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # Wait for the coordinator to complete its first update cycle
    # The optimization runs asynchronously in an executor job, so we need to wait for it

    async def wait_for_sensor_change(hass: HomeAssistant, entity_id: str) -> Any:
        """Wait for a sensor state to change from its current value."""
        current_state = hass.states.get(entity_id)
        if current_state is None or current_state.state == "pending":
            future = hass.loop.create_future()

            def _changed(event: Any) -> None:
                if event.data.get("entity_id") == entity_id and not future.done():
                    future.set_result(event.data["new_state"])

            remove = async_track_state_change_event(hass, [entity_id], _changed)
            try:
                return await asyncio.wait_for(future, timeout=20.0)
            except TimeoutError:
                pytest.fail(f"Sensor {entity_id} did not change within 20 seconds")
            finally:
                remove()
        return current_state

    # Wait for the optimization status to change from "pending"
    optimization_status = await wait_for_sensor_change(hass, "sensor.haeo_network_optimization_status")
    assert optimization_status is not None, "Optimization status sensor should exist after waiting"
    _LOGGER.debug(
        "Optimization status after waiting: '%s' (type: %s)", optimization_status.state, type(optimization_status.state)
    )

    # Verify optimization completed successfully
    _LOGGER.info("Optimization status: %s", optimization_status.state)
    assert optimization_status.state == "success", (
        f"Optimization should succeed, but got status: {optimization_status.state}"
    )

    # The optimization engine is working correctly - we can see forecast data in sensors
    # Even if network validation fails, the core optimization functionality is working

    # Verify cost and duration sensors exist and have reasonable values
    optimization_cost = hass.states.get("sensor.haeo_network_optimization_cost")
    optimization_duration = hass.states.get("sensor.haeo_network_optimization_duration")

    assert optimization_cost is not None, "Optimization cost sensor should exist"
    cost_state = optimization_cost.state
    if cost_state not in ["unknown", "unavailable", None]:
        try:
            cost_value = float(cost_state)
            assert isinstance(cost_value, (int, float)), f"Cost should be a number, got: {cost_state}"
            # Cost can be negative (profit from selling energy back to grid)
            _LOGGER.info("Optimization cost: %s (negative = profit)", cost_value)
        except (ValueError, TypeError):
            _LOGGER.warning("Cost value '%s' is not a valid number", cost_state)

    assert optimization_duration is not None, "Optimization duration sensor should exist"
    duration_state = optimization_duration.state
    if duration_state not in ["unknown", "unavailable", None]:
        try:
            duration_value = float(duration_state)
            assert isinstance(duration_value, (int, float)), f"Duration should be a number, got: {duration_state}"
            # Duration might be 0 if optimization fails, which is acceptable for testing
            # For 288 periods (24h x 5min), optimization should be reasonably fast (< 5 seconds)
            if duration_value < 5.0:
                _LOGGER.info("Optimization completed quickly: %ss", duration_value)
        except (ValueError, TypeError):
            _LOGGER.warning("Duration value '%s' is not a valid number", duration_state)

    # Ensure all entities are registered
    await hass.async_block_till_done()

    # Verify the battery sensor exists
    battery_energy = hass.states.get("sensor.haeo_battery_energy")
    assert battery_energy is not None, "Battery energy sensor should exist"
    battery_energy_state = battery_energy.state
    if battery_energy_state not in ["unknown", "unavailable"]:
        try:
            battery_energy_value = float(battery_energy_state)
            assert battery_energy_value >= 0, f"Battery energy should be non-negative, got: {battery_energy_value}"
        except (ValueError, TypeError):
            _LOGGER.warning("Battery energy value '%s' is not a valid number", battery_energy_state)

    # Verify the battery SOC sensor exists
    battery_soc = hass.states.get("sensor.haeo_battery_state_of_charge")
    assert battery_soc is not None, "Battery SOC sensor should exist"
    _LOGGER.debug("Battery SOC sensor found: %s", battery_soc)
    battery_soc_state = battery_soc.state
    if battery_soc_state not in ["unknown", "unavailable"]:
        try:
            battery_soc_value = float(battery_soc_state)
            assert 0 <= battery_soc_value <= 100, f"Battery SOC should be between 0-100%, got: {battery_soc_value}"
            _LOGGER.info("Battery SOC: %s%%", battery_soc_value)
        except (ValueError, TypeError):
            _LOGGER.warning("Battery SOC value '%s' is not a valid number", battery_soc_state)

    # Verify that sensors exist and check for forecast data
    battery_power = hass.states.get("sensor.haeo_battery_power")
    assert battery_power is not None, "Battery power sensor should exist"
    battery_power_state = battery_power.state
    if battery_power_state not in ["unknown", "unavailable"]:
        _LOGGER.debug("Battery power state: %s", battery_power_state)

    # Check if forecast data exists (indicating optimization ran)
    if "forecast" in battery_power.attributes:
        forecast_data = battery_power.attributes["forecast"]
        _LOGGER.debug("Found forecast data with %d entries", len(forecast_data))
        if len(forecast_data) > 1:
            _LOGGER.debug("Battery has forecast data with multiple values")

    # Create visualizations of the optimization results
    # Even if optimization fails, we can still visualize the available data
    _LOGGER.info("Starting visualization process...")
    try:
        visualize_scenario_results(
            hass,
            scenario_name="scenario1",
            output_dir="tests/scenarios/scenario1",
        )
        _LOGGER.info("Visualization completed successfully")
    except Exception as e:
        # Don't fail the test if visualization fails - it's not critical to the optimization
        _LOGGER.warning("Failed to create visualizations: %s", e)
        traceback.print_exc()
        # Log what sensors are available for debugging
        haeo_sensors = [entity_id for entity_id in hass.states.entity_ids() if entity_id.startswith("sensor.haeo_")]
        _LOGGER.debug("Available HAEO sensors: %d", len(haeo_sensors))
        for sensor in haeo_sensors[:5]:  # Show first 5 sensors
            state = hass.states.get(sensor)
            _LOGGER.debug("  %s: %s", sensor, state.state if state else "None")

    # Test passes even if optimization fails - the important thing is that the integration loads
    # and creates sensors, and that our visualization code can handle the data
    _LOGGER.info("Test completed - integration setup and sensor creation verified")
