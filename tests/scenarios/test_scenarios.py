"""Centralized parameterized test runner for all scenario tests."""

import asyncio
import logging
import os
from pathlib import Path
from types import MappingProxyType
from typing import Any

from freezegun import freeze_time
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_ELEMENT_TYPE,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
)
from custom_components.haeo.sensor_utils import get_output_sensors
from tests.scenarios.conftest import ScenarioData
from tests.scenarios.visualization import visualize_scenario_results

_LOGGER = logging.getLogger(__name__)


def _discover_scenarios() -> list[Path]:
    """Discover all scenario folders."""
    scenarios_dir = Path(__file__).parent
    return sorted(scenarios_dir.glob("scenario*/"))


# Discover scenarios for test parameters
_scenarios = _discover_scenarios()


# Skip if in CI
@pytest.mark.skipif(os.getenv("CI") == "true", reason="Skipping scenario tests in CI")
@pytest.mark.scenario
@pytest.mark.timeout(30)
@pytest.mark.parametrize(
    "scenario_path",
    _scenarios,
    ids=[scenario.name for scenario in _scenarios],
    indirect=["scenario_path"],
)
async def test_scenarios(
    hass: HomeAssistant,
    scenario_path: Path,
    scenario_data: ScenarioData,
    snapshot: Any,
) -> None:
    """Test that scenario sets up correctly and optimization matches expected outputs."""
    # Extract freeze timestamp from scenario data
    freeze_timestamp = scenario_data["environment"]["timestamp"]

    # Apply freeze_time dynamically
    with freeze_time(freeze_timestamp):
        # Set up sensor states from scenario data and wait until they are loaded
        for state_data in scenario_data["inputs"]:
            hass.states.async_set(state_data["entity_id"], state_data["state"], state_data.get("attributes", {}))
        await hass.async_block_till_done()

        # Create hub config entry and add to hass
        scenario_config = scenario_data["config"]
        mock_config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "integration_type": INTEGRATION_TYPE_HUB,
                CONF_NAME: "Test Hub",
                CONF_TIER_1_COUNT: scenario_config["tier_1_count"],
                CONF_TIER_1_DURATION: scenario_config["tier_1_duration"],
                CONF_TIER_2_COUNT: scenario_config.get("tier_2_count", 0),
                CONF_TIER_2_DURATION: scenario_config.get("tier_2_duration", 5),
                CONF_TIER_3_COUNT: scenario_config.get("tier_3_count", 0),
                CONF_TIER_3_DURATION: scenario_config.get("tier_3_duration", 30),
                CONF_TIER_4_COUNT: scenario_config.get("tier_4_count", 0),
                CONF_TIER_4_DURATION: scenario_config.get("tier_4_duration", 60),
            },
        )
        mock_config_entry.add_to_hass(hass)

        # Create element subentries from the scenario config
        for name, config in scenario_config["participants"].items():
            subentry = ConfigSubentry(
                data=MappingProxyType(config), subentry_type=config[CONF_ELEMENT_TYPE], title=name, unique_id=None
            )
            hass.config_entries.async_add_subentry(mock_config_entry, subentry)

        # Now set up the hub - coordinator will find the subentries via _get_child_elements()
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Get the coordinator from the config entry
        coordinator = mock_config_entry.runtime_data
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

        entity_registry = er.async_get(hass)
        status_entity_entry = next(
            (
                entry
                for entry in er.async_entries_for_config_entry(entity_registry, mock_config_entry.entry_id)
                if entry.unique_id.endswith(f"_{OUTPUT_NAME_OPTIMIZATION_STATUS}")
            ),
            None,
        )
        assert status_entity_entry is not None, "Optimization status entity should be registered"

        optimization_status = await wait_for_sensor_change(hass, status_entity_entry.entity_id)
        assert optimization_status is not None, "Optimization status sensor should exist after waiting"
        _LOGGER.debug(
            "Optimization status after waiting: '%s' (type: %s)",
            optimization_status.state,
            type(optimization_status.state),
        )

        # Verify optimization completed successfully
        _LOGGER.info("Optimization status: %s", optimization_status.state)
        assert optimization_status.state == "success", (
            f"Optimization should succeed, but got status: {optimization_status.state}"
        )

        # The optimization engine is working correctly - we can see forecast data in sensors
        # Even if network validation fails, the core optimization functionality is working

        # Ensure all entities are registered
        await hass.async_block_till_done()

        # Get output sensors using common utility function
        # This filters to entities created by this config entry and cleans unstable fields
        output_sensors = get_output_sensors(hass, mock_config_entry)

        # Create visualizations from the output sensors
        _LOGGER.info("Starting visualization process...")
        visualize_scenario_results(
            output_sensors,
            scenario_path.name,
            scenario_path / "visualizations",
            scenario_config,
        )

        # Compare actual outputs with expected outputs using snapshot
        _LOGGER.info("Comparing %d actual outputs with expected outputs", len(output_sensors))
        assert output_sensors == snapshot
