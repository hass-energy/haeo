"""Tests for HAEO diagnostics utilities."""

from datetime import UTC, datetime
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
from custom_components.haeo.model.const import OUTPUT_NAME_POWER_CONSUMED, OUTPUT_TYPE_POWER


async def test_diagnostics_basic_structure(hass: HomeAssistant) -> None:
    """Diagnostics returns correct structure with four main keys in the right order."""
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

    # Verify the four main keys
    assert "config" in diagnostics
    assert "inputs" in diagnostics
    assert "outputs" in diagnostics
    assert "environment" in diagnostics

    # Verify key order: config, environment, inputs, outputs
    keys = list(diagnostics.keys())
    assert keys == ["config", "environment", "inputs", "outputs"]

    # Verify config structure
    assert diagnostics["config"][CONF_HORIZON_HOURS] == 24
    assert diagnostics["config"][CONF_PERIOD_MINUTES] == 15
    assert "participants" in diagnostics["config"]

    # Verify environment
    assert "ha_version" in diagnostics["environment"]
    assert "haeo_version" in diagnostics["environment"]
    assert "timestamp" in diagnostics["environment"]
    assert "timezone" in diagnostics["environment"]


async def test_diagnostics_with_participants(hass: HomeAssistant) -> None:
    """Diagnostics includes participant configs."""
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

    # Verify config has participants
    participants = diagnostics["config"]["participants"]
    assert "Battery One" in participants
    battery_config = participants["Battery One"]
    assert battery_config[CONF_ELEMENT_TYPE] == ELEMENT_TYPE_BATTERY
    assert battery_config[CONF_NAME] == "Battery One"
    assert battery_config[CONF_CAPACITY] == 5000.0
    assert battery_config[CONF_INITIAL_CHARGE_PERCENTAGE] == "sensor.battery_soc"

    # Verify input states are collected using State.as_dict()
    inputs = diagnostics["inputs"]
    assert len(inputs) == 1
    assert inputs[0]["entity_id"] == "sensor.battery_soc"
    assert inputs[0]["state"] == "75"
    assert "attributes" in inputs[0]
    assert "last_updated" in inputs[0]

    # Verify outputs is empty when no coordinator
    assert diagnostics["outputs"] == []


async def test_diagnostics_with_outputs(hass: HomeAssistant) -> None:
    """Diagnostics includes output sensor states when coordinator available."""
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
        },
    )

    # Create a mock coordinator with outputs
    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.data = {
        "grid": {
            OUTPUT_NAME_POWER_CONSUMED: CoordinatorOutput(
                type=OUTPUT_TYPE_POWER,
                unit="kW",
                state=5.5,
                forecast={datetime(2024, 1, 1, 12, 0, tzinfo=UTC): 5.5},
            )
        }
    }

    # Set up output sensor state
    hass.states.async_set(
        f"sensor.{DOMAIN}_hub_entry_{grid_subentry.subentry_id}_{OUTPUT_NAME_POWER_CONSUMED}",
        "5.5",
        {
            "unit_of_measurement": "kW",
            "element_name": "Grid",
        },
    )

    entry.runtime_data = coordinator

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    # Verify outputs are collected
    outputs = diagnostics["outputs"]
    assert len(outputs) >= 1
    output_entity = next(
        (s for s in outputs if OUTPUT_NAME_POWER_CONSUMED in s["entity_id"]),
        None,
    )
    assert output_entity is not None
    assert output_entity["state"] == "5.5"
