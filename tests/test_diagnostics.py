"""Test HAEO diagnostics."""

from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.diagnostics import async_get_config_entry_diagnostics
from custom_components.haeo.model.network import Network


async def test_diagnostics_empty_network(hass: HomeAssistant) -> None:
    """Test diagnostics with empty network."""
    # Create hub entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            "name": "Test Hub",
        },
        entry_id="test_hub",
    )
    config_entry.add_to_hass(hass)

    # Setup integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Get diagnostics
    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    # Verify structure
    assert "config_entry" in diagnostics
    assert "hub_config" in diagnostics
    assert "subentries" in diagnostics
    assert "coordinator" in diagnostics

    # Verify config entry data
    assert diagnostics["config_entry"]["entry_id"] == "test_hub"
    assert diagnostics["config_entry"]["version"] == 1
    assert diagnostics["config_entry"]["domain"] == DOMAIN

    # Verify hub config is present
    assert "horizon_hours" in diagnostics["hub_config"]
    assert "period_minutes" in diagnostics["hub_config"]
    assert "optimizer" in diagnostics["hub_config"]

    # Verify subentries (network should be auto-created)
    assert isinstance(diagnostics["subentries"], list)

    # Verify coordinator state
    assert diagnostics["coordinator"]["last_update_success"] is not None
    assert diagnostics["coordinator"]["update_interval"] is not None


async def test_diagnostics_with_subentries(hass: HomeAssistant) -> None:
    """Test diagnostics with multiple subentries."""
    # Create hub entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            "name": "Test Hub",
        },
        entry_id="test_hub",
    )
    config_entry.add_to_hass(hass)

    # Add battery subentry
    battery = ConfigSubentry(
        data=MappingProxyType(
            {
                "name_value": "Battery 1",
                "capacity_value": 10000.0,
                "charge_rate_value": 5000.0,
            }
        ),
        subentry_type="battery",
        title="Battery 1",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(config_entry, battery)

    # Setup integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Get diagnostics
    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    # Verify subentries are captured
    assert len(diagnostics["subentries"]) >= 1

    # Find battery in subentries
    battery_info = next((s for s in diagnostics["subentries"] if s["subentry_type"] == "battery"), None)
    assert battery_info is not None
    assert battery_info["name"] == "Battery 1"
    assert "config" in battery_info
    assert battery_info["config"]["capacity_value"] == 10000.0


async def test_diagnostics_with_optimization_results(hass: HomeAssistant) -> None:
    """Test diagnostics with optimization results."""
    # Create hub entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            "name": "Test Hub",
        },
        entry_id="test_hub",
    )
    config_entry.add_to_hass(hass)

    # Create mock coordinator with optimization results
    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.optimization_status = "success"
    coordinator.last_update_success = True
    coordinator.update_interval = timedelta(minutes=5)
    coordinator.last_optimization_time = datetime.now(UTC)
    coordinator.last_optimization_duration = 1.5
    coordinator.last_optimization_cost = 123.45

    # Create mock network with elements
    network = Mock(spec=Network)
    network.elements = {
        "battery_1": Mock(),
        "grid_1": Mock(),
        "connection_battery_1_grid_1": Mock(source="battery_1", target="grid_1"),
    }
    coordinator.network = network

    # Mock optimization result
    coordinator.optimization_result = Mock()
    coordinator.get_element_data = Mock(
        return_value={
            "power": [100, 200, 300],
            "energy": [1000, 2000, 3000],
            "soc": [50, 60, 70],
        }
    )

    # Set runtime data
    config_entry.runtime_data = coordinator

    # Get diagnostics
    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    # Verify optimization results
    assert "last_optimization" in diagnostics
    assert diagnostics["last_optimization"]["status"] == "success"
    assert diagnostics["last_optimization"]["duration_seconds"] == 1.5
    assert diagnostics["last_optimization"]["cost"] == 123.45

    # Verify network structure
    assert "network" in diagnostics
    assert diagnostics["network"]["num_elements"] == 3
    assert "battery_1" in diagnostics["network"]["element_names"]
    assert "grid_1" in diagnostics["network"]["element_names"]

    # Verify connections
    assert len(diagnostics["network"]["connections"]) == 1
    assert diagnostics["network"]["connections"][0]["from"] == "battery_1"
    assert diagnostics["network"]["connections"][0]["to"] == "grid_1"

    # Verify element results
    assert "optimization_results" in diagnostics
    assert "battery_1" in diagnostics["optimization_results"]
    assert diagnostics["optimization_results"]["battery_1"]["has_power_data"] is True
    assert diagnostics["optimization_results"]["battery_1"]["has_energy_data"] is True
    assert diagnostics["optimization_results"]["battery_1"]["has_soc_data"] is True
    assert diagnostics["optimization_results"]["battery_1"]["num_periods"] == 3


async def test_diagnostics_with_element_data_error(hass: HomeAssistant) -> None:
    """Test diagnostics when element data retrieval fails."""
    # Create hub entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            "name": "Test Hub",
        },
        entry_id="test_hub",
    )
    config_entry.add_to_hass(hass)

    # Create mock coordinator with optimization results but failing get_element_data
    coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    coordinator.optimization_status = "success"
    coordinator.last_update_success = True
    coordinator.update_interval = timedelta(minutes=5)
    coordinator.last_optimization_time = None

    # Create mock network
    network = Mock(spec=Network)
    network.elements = {"battery_1": Mock()}
    coordinator.network = network

    # Mock optimization result with failing get_element_data
    coordinator.optimization_result = Mock()
    coordinator.get_element_data = Mock(side_effect=Exception("Test error"))

    # Set runtime data
    config_entry.runtime_data = coordinator

    # Get diagnostics
    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    # Verify error is handled gracefully
    assert "optimization_results" in diagnostics
    assert "battery_1" in diagnostics["optimization_results"]
    assert "error" in diagnostics["optimization_results"]["battery_1"]
    assert diagnostics["optimization_results"]["battery_1"]["error"] == "Failed to retrieve data"


async def test_diagnostics_with_no_coordinator(hass: HomeAssistant) -> None:
    """Test diagnostics with no coordinator (runtime_data is None)."""
    # Create hub entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            "name": "Test Hub",
        },
        entry_id="test_hub",
    )
    config_entry.add_to_hass(hass)

    # Set runtime_data to None explicitly
    config_entry.runtime_data = None

    # Get diagnostics
    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    # Verify basic structure still present
    assert "config_entry" in diagnostics
    assert "hub_config" in diagnostics
    assert "subentries" in diagnostics

    # Coordinator sections should not be present
    assert "coordinator" not in diagnostics
    assert "last_optimization" not in diagnostics
    assert "network" not in diagnostics
