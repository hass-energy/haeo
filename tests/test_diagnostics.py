"""Tests for HAEO diagnostics utilities."""

from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_ELEMENT_TYPE,
    CONF_HORIZON_HOURS,
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    CONF_PERIOD_MINUTES,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.coordinator import CoordinatorOutput, HaeoDataUpdateCoordinator
from custom_components.haeo.diagnostics import async_get_config_entry_diagnostics
from custom_components.haeo.elements import ELEMENT_TYPE_BATTERY
from custom_components.haeo.elements.battery import CONF_CAPACITY, CONF_INITIAL_CHARGE_PERCENTAGE
from custom_components.haeo.elements.grid import CONF_IMPORT_PRICE
from custom_components.haeo.model.const import (
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
    OUTPUT_NAME_POWER_CONSUMED,
    OUTPUT_TYPE_COST,
    OUTPUT_TYPE_DURATION,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_STATUS,
)


async def test_diagnostics_without_coordinator(hass: HomeAssistant) -> None:
    """Diagnostics return basic configuration when runtime data is absent."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_HORIZON_HOURS: 24,
            CONF_PERIOD_MINUTES: 15,
        },
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)
    entry.runtime_data = None

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["config_entry"]["entry_id"] == "test_entry"
    assert "hub_config" in diagnostics
    assert "subentries" in diagnostics
    assert "coordinator" not in diagnostics


async def test_diagnostics_summarise_outputs(hass: HomeAssistant) -> None:
    """Diagnostics include coordinator metadata and output summaries."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_HORIZON_HOURS: 24,
            CONF_PERIOD_MINUTES: 15,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
                CONF_NAME: "Battery One",
                CONF_CAPACITY: 5000.0,
                CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
            }
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Battery One",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.last_update_success = True
    coordinator.update_interval = timedelta(minutes=5)
    coordinator.last_update_success_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    forecast_map = {
        datetime(2024, 1, 1, 12, 0, tzinfo=UTC): 3.0,
        datetime(2024, 1, 1, 12, 15, tzinfo=UTC): 2.5,
        datetime(2024, 1, 1, 12, 30, tzinfo=UTC): 2.0,
    }
    coordinator.data = {
        "test_hub": {
            OUTPUT_NAME_OPTIMIZATION_STATUS: CoordinatorOutput(
                type=OUTPUT_TYPE_STATUS,
                unit=None,
                state="success",
                forecast=None,
            ),
            OUTPUT_NAME_OPTIMIZATION_COST: CoordinatorOutput(
                type=OUTPUT_TYPE_COST,
                unit="$",
                state=27.5,
                forecast=None,
            ),
            OUTPUT_NAME_OPTIMIZATION_DURATION: CoordinatorOutput(
                type=OUTPUT_TYPE_DURATION,
                unit="s",
                state=1.25,
                forecast=None,
            ),
        },
        "battery_one": {
            OUTPUT_NAME_POWER_CONSUMED: CoordinatorOutput(
                type=OUTPUT_TYPE_POWER,
                unit="kW",
                state=3.0,
                forecast=forecast_map,
            )
        },
    }

    # Provide a lightweight network structure for diagnostics
    network = Mock()
    network.elements = {
        "battery_one": Mock(name="battery_one"),
        "connection_grid": Mock(name="connection_grid", source="battery_one", target="grid"),
    }
    coordinator.network = network

    entry.runtime_data = coordinator

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["coordinator"]["optimization_status"] == "success"
    assert diagnostics["last_optimization"]["cost"] == 27.5

    outputs = diagnostics["outputs"]["battery_one"][OUTPUT_NAME_POWER_CONSUMED]
    assert outputs["type"] == OUTPUT_TYPE_POWER
    assert outputs["unit"] == "kW"
    assert outputs["value_count"] == 3
    assert outputs["first_value"] == 3.0
    assert outputs["has_forecast"] is True

    assert diagnostics["network"]["num_elements"] == 2
    assert diagnostics["network"]["connections"] == [{"from": "battery_one", "to": "grid"}]


async def test_diagnostics_handles_missing_outputs(hass: HomeAssistant) -> None:
    """When coordinator has no data, diagnostics omit the outputs section."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.last_update_success = False
    coordinator.update_interval = None
    coordinator.last_update_success_time = None
    coordinator.data = {}
    coordinator.network = None

    entry.runtime_data = coordinator

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["coordinator"]["optimization_status"] == "pending"
    assert "outputs" not in diagnostics
    assert "network" not in diagnostics


async def test_diagnostics_scenario_format(hass: HomeAssistant) -> None:
    """Diagnostics include scenario format compatible with test scenarios."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_HORIZON_HOURS: 24,
            CONF_PERIOD_MINUTES: 15,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE_BATTERY,
                CONF_NAME: "Battery One",
                CONF_CAPACITY: 5000.0,
                CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
            }
        ),
        subentry_type=ELEMENT_TYPE_BATTERY,
        title="Battery One",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    # Set up a sensor state that should be captured
    hass.states.async_set(
        "sensor.battery_soc",
        "75",
        {
            "unit_of_measurement": "%",
            "device_class": "battery",
        },
    )

    entry.runtime_data = None

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify scenario_format section exists
    assert "scenario_format" in diagnostics
    scenario_format = diagnostics["scenario_format"]

    # Verify config matches scenario format
    assert "config" in scenario_format
    scenario_config = scenario_format["config"]
    assert scenario_config[CONF_HORIZON_HOURS] == 24
    assert scenario_config[CONF_PERIOD_MINUTES] == 15
    assert "participants" in scenario_config

    # Verify participants are properly formatted
    participants = scenario_config["participants"]
    assert "Battery One" in participants
    battery_config = participants["Battery One"]
    assert battery_config[CONF_ELEMENT_TYPE] == ELEMENT_TYPE_BATTERY
    assert battery_config[CONF_NAME] == "Battery One"
    assert battery_config[CONF_CAPACITY] == 5000.0
    assert battery_config[CONF_INITIAL_CHARGE_PERCENTAGE] == "sensor.battery_soc"

    # Verify states are collected
    assert "states" in scenario_format
    states = scenario_format["states"]
    assert len(states) == 1
    assert states[0]["entity_id"] == "sensor.battery_soc"
    assert states[0]["state"] == "75"
    assert "attributes" in states[0]
    assert "last_updated" in states[0]

    # Verify output_states is included but None when no coordinator
    assert "output_states" in scenario_format
    assert scenario_format["output_states"] is None


async def test_diagnostics_scenario_format_with_outputs(hass: HomeAssistant) -> None:
    """Diagnostics scenario format includes output sensor states when available."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_HORIZON_HOURS: 24,
            CONF_PERIOD_MINUTES: 15,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    # Add a grid subentry that uses a price sensor
    grid_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: "grid",
                CONF_NAME: "Grid",
                CONF_IMPORT_PRICE: ["sensor.grid_import_price"],
            }
        ),
        subentry_type="grid",
        title="Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, grid_subentry)

    # Set up input sensor states
    hass.states.async_set(
        "sensor.grid_import_price",
        "0.25",
        {
            "unit_of_measurement": "$/kWh",
            "forecast": {"2024-01-01T12:00:00": 0.25, "2024-01-01T12:15:00": 0.30},
        },
    )

    # Create a mock coordinator with outputs
    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.last_update_success = True
    coordinator.update_interval = timedelta(minutes=5)
    coordinator.data = {
        "grid": {
            OUTPUT_NAME_POWER_CONSUMED: CoordinatorOutput(
                type=OUTPUT_TYPE_POWER,
                unit="kW",
                state=5.5,
                forecast={datetime(2024, 1, 1, 12, 0, tzinfo=UTC): 5.5, datetime(2024, 1, 1, 12, 15, tzinfo=UTC): 6.0},
            )
        }
    }
    coordinator.network = None

    # Set up output sensor state (simulating what would be created)
    hass.states.async_set(
        f"sensor.{DOMAIN}_hub_entry_{grid_subentry.subentry_id}_{OUTPUT_NAME_POWER_CONSUMED}",
        "5.5",
        {
            "unit_of_measurement": "kW",
            "forecast": {"2024-01-01T12:00:00+00:00": 5.5, "2024-01-01T12:15:00+00:00": 6.0},
            "element_name": "Grid",
            "element_type": "grid",
            "output_name": OUTPUT_NAME_POWER_CONSUMED,
        },
    )

    entry.runtime_data = coordinator

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify scenario format includes both input and output states
    scenario_format = diagnostics["scenario_format"]

    # Verify input states
    states = scenario_format["states"]
    assert len(states) == 1
    assert states[0]["entity_id"] == "sensor.grid_import_price"

    # Verify output states are collected when coordinator is available
    output_states = scenario_format["output_states"]
    assert output_states is not None
    assert len(output_states) >= 1
    output_entity = next(
        (s for s in output_states if OUTPUT_NAME_POWER_CONSUMED in s["entity_id"]),
        None,
    )
    assert output_entity is not None
    assert output_entity["state"] == "5.5"
    assert "forecast" in output_entity["attributes"]
