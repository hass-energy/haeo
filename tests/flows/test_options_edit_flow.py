"""Tests for the options flow edit functionality."""

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.flows.options import HubOptionsFlow


async def test_edit_flow_preserves_current_config_on_form_resubmit(hass: HomeAssistant) -> None:
    """Test that editing a participant preserves the current config when form has errors."""
    # Create a config entry with a battery participant
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": "hub",
            "name": "Test Hub",
            "horizon_hours": 24,
            "period_minutes": 30,
            "optimizer": "highs",
            "participants": {
                "My Battery": {
                    "type": "battery",
                    "name_value": "My Battery",
                    "capacity_value": 10.0,
                    "initial_charge_percentage_value": "sensor.battery_soc",
                    "min_charge_percentage_value": 20.0,
                    "max_charge_percentage_value": 90.0,
                    "max_charge_power_value": 5.0,
                    "max_discharge_power_value": 5.0,
                    "efficiency_value": 0.95,
                },
            },
        },
    )
    config_entry.add_to_hass(hass)

    # Initialize the options flow
    flow = HubOptionsFlow()
    flow.hass = hass
    flow._config_entry = config_entry

    # Start edit flow - select the battery
    result = await flow.async_step_edit_participant({"participant": "My Battery"})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "configure_battery"

    # Verify the flow stored the editing participant
    assert flow._editing_participant is not None
    assert flow._editing_participant["name_value"] == "My Battery"

    # Submit with a duplicate name that causes an error
    config_entry.data["participants"]["Other Battery"] = {
        "type": "battery",
        "name_value": "Other Battery",
    }

    result = await flow.async_step_configure_battery({"name_value": "Other Battery"})
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["name_value"] == "name_exists"

    # The editing state should still be preserved
    assert flow._editing_participant is not None
    assert flow._editing_participant["name_value"] == "My Battery"


async def test_edit_flow_prevents_duplicate_names_except_current(hass: HomeAssistant) -> None:
    """Test that editing prevents duplicate names but allows keeping the current name."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": "hub",
            "name": "Test Hub",
            "horizon_hours": 24,
            "period_minutes": 30,
            "optimizer": "highs",
            "participants": {
                "Battery 1": {
                    "type": "battery",
                    "name_value": "Battery 1",
                    "capacity_value": 10.0,
                },
                "Battery 2": {
                    "type": "battery",
                    "name_value": "Battery 2",
                    "capacity_value": 10.0,
                },
            },
        },
    )
    config_entry.add_to_hass(hass)

    flow = HubOptionsFlow()
    flow.hass = hass
    flow._config_entry = config_entry

    # Start editing Battery 1
    await flow.async_step_edit_participant({"participant": "Battery 1"})

    # Try to rename to Battery 2 (should fail - duplicate)
    result = await flow.async_step_configure_battery(
        {
            "name_value": "Battery 2",
            "capacity_value": 10.0,
            "initial_charge_percentage_value": "sensor.battery_soc",
            "min_charge_percentage_value": 20.0,
            "max_charge_percentage_value": 90.0,
            "max_charge_power_value": 5.0,
            "max_discharge_power_value": 5.0,
            "efficiency_value": 0.95,
        }
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["name_value"] == "name_exists"

    # Keep the same name (should succeed)
    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        result = await flow.async_step_configure_battery(
            {
                "name_value": "Battery 1",  # Same name - should be allowed
                "capacity_value": 15.0,  # Changed value
                "initial_charge_percentage_value": "sensor.battery_soc",
                "min_charge_percentage_value": 20.0,
                "max_charge_percentage_value": 90.0,
                "max_charge_power_value": 5.0,
                "max_discharge_power_value": 5.0,
                "efficiency_value": 0.95,
            }
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    # Verify the update was saved
    assert config_entry.data["participants"]["Battery 1"]["capacity_value"] == 15.0


async def test_edit_flow_renames_participant_correctly(hass: HomeAssistant) -> None:
    """Test that renaming a participant updates the dictionary key."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": "hub",
            "name": "Test Hub",
            "horizon_hours": 24,
            "period_minutes": 30,
            "optimizer": "highs",
            "participants": {
                "Old Battery Name": {
                    "type": "battery",
                    "name_value": "Old Battery Name",
                    "capacity_value": 10.0,
                },
            },
        },
    )
    config_entry.add_to_hass(hass)

    flow = HubOptionsFlow()
    flow.hass = hass
    flow._config_entry = config_entry

    # Start editing
    await flow.async_step_edit_participant({"participant": "Old Battery Name"})

    # Rename to a new name
    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        result = await flow.async_step_configure_battery(
            {
                "name_value": "New Battery Name",
                "capacity_value": 10.0,
                "initial_charge_percentage_value": "sensor.battery_soc",
                "min_charge_percentage_value": 20.0,
                "max_charge_percentage_value": 90.0,
                "max_charge_power_value": 5.0,
                "max_discharge_power_value": 5.0,
                "efficiency_value": 0.95,
            }
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Verify old name is removed and new name exists
    participants = config_entry.data["participants"]
    assert "Old Battery Name" not in participants
    assert "New Battery Name" in participants
    assert participants["New Battery Name"]["name_value"] == "New Battery Name"
    assert participants["New Battery Name"]["capacity_value"] == 10.0


async def test_edit_flow_updates_connection_references_on_rename(hass: HomeAssistant) -> None:
    """Test that renaming a participant updates connection source/target references."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": "hub",
            "name": "Test Hub",
            "horizon_hours": 24,
            "period_minutes": 30,
            "optimizer": "highs",
            "participants": {
                "Battery": {
                    "type": "battery",
                    "name_value": "Battery",
                    "capacity_value": 10.0,
                },
                "Grid": {
                    "type": "grid",
                    "name_value": "Grid",
                },
                "Net Node": {
                    "type": "node",
                    "name_value": "Net Node",
                },
                "Battery to Net": {
                    "type": "connection",
                    "name_value": "Battery to Net",
                    "source_value": "Battery",
                    "target_value": "Net Node",
                    "min_power_value": 0.0,
                    "max_power_value": 5.0,
                },
                "Grid to Net": {
                    "type": "connection",
                    "name_value": "Grid to Net",
                    "source_value": "Grid",
                    "target_value": "Net Node",
                    "min_power_value": 0.0,
                    "max_power_value": 10.0,
                },
            },
        },
    )
    config_entry.add_to_hass(hass)

    flow = HubOptionsFlow()
    flow.hass = hass
    flow._config_entry = config_entry

    # Rename "Battery" to "My Battery"
    await flow.async_step_edit_participant({"participant": "Battery"})

    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        result = await flow.async_step_configure_battery(
            {
                "name_value": "My Battery",
                "capacity_value": 10.0,
                "initial_charge_percentage_value": "sensor.battery_soc",
                "min_charge_percentage_value": 20.0,
                "max_charge_percentage_value": 90.0,
                "max_charge_power_value": 5.0,
                "max_discharge_power_value": 5.0,
                "efficiency_value": 0.95,
            }
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Verify the battery was renamed
    participants = config_entry.data["participants"]
    assert "Battery" not in participants
    assert "My Battery" in participants

    # Verify the connection source reference was updated
    assert participants["Battery to Net"]["source_value"] == "My Battery"

    # Verify other connection was NOT updated (different source)
    assert participants["Grid to Net"]["source_value"] == "Grid"


async def test_edit_flow_updates_connection_target_references_on_rename(hass: HomeAssistant) -> None:
    """Test that renaming updates connection target references."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": "hub",
            "name": "Test Hub",
            "horizon_hours": 24,
            "period_minutes": 30,
            "optimizer": "highs",
            "participants": {
                "Battery": {
                    "type": "battery",
                    "name_value": "Battery",
                },
                "Old Net": {
                    "type": "node",
                    "name_value": "Old Net",
                },
                "Connection": {
                    "type": "connection",
                    "name_value": "Connection",
                    "source_value": "Battery",
                    "target_value": "Old Net",
                    "min_power_value": 0.0,
                    "max_power_value": 5.0,
                },
            },
        },
    )
    config_entry.add_to_hass(hass)

    flow = HubOptionsFlow()
    flow.hass = hass
    flow._config_entry = config_entry

    # Rename "Old Net" to "New Net"
    await flow.async_step_edit_participant({"participant": "Old Net"})

    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        result = await flow.async_step_configure_node(
            {
                "name_value": "New Net",
            }
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Verify the connection target reference was updated
    participants = config_entry.data["participants"]
    assert participants["Connection"]["target_value"] == "New Net"


async def test_edit_flow_clears_editing_state_after_successful_update(hass: HomeAssistant) -> None:
    """Test that the editing state is cleared after a successful update."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": "hub",
            "name": "Test Hub",
            "horizon_hours": 24,
            "period_minutes": 30,
            "optimizer": "highs",
            "participants": {
                "Battery": {
                    "type": "battery",
                    "name_value": "Battery",
                    "capacity_value": 10.0,
                },
            },
        },
    )
    config_entry.add_to_hass(hass)

    flow = HubOptionsFlow()
    flow.hass = hass
    flow._config_entry = config_entry

    # Start editing
    await flow.async_step_edit_participant({"participant": "Battery"})
    assert flow._editing_participant is not None

    # Complete the edit
    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        result = await flow.async_step_configure_battery(
            {
                "name_value": "Battery",
                "capacity_value": 15.0,
                "initial_charge_percentage_value": "sensor.battery_soc",
                "min_charge_percentage_value": 20.0,
                "max_charge_percentage_value": 90.0,
                "max_charge_power_value": 5.0,
                "max_discharge_power_value": 5.0,
                "efficiency_value": 0.95,
            }
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    # Verify editing state was cleared
    assert flow._editing_participant is None


async def test_add_flow_clears_editing_state(hass: HomeAssistant) -> None:
    """Test that starting an add flow clears any stale editing state."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": "hub",
            "name": "Test Hub",
            "horizon_hours": 24,
            "period_minutes": 30,
            "optimizer": "highs",
            "participants": {
                "Battery": {
                    "type": "battery",
                    "name_value": "Battery",
                },
            },
        },
    )
    config_entry.add_to_hass(hass)

    flow = HubOptionsFlow()
    flow.hass = hass
    flow._config_entry = config_entry

    # Simulate stale editing state
    flow._editing_participant = {"name_value": "Stale Battery"}

    # Start an add flow
    result = await flow.async_step_add_participant({"participant_type": "battery"})

    assert result["type"] == FlowResultType.FORM
    # Verify editing state was cleared
    assert flow._editing_participant is None


async def test_add_flow_clears_editing_state_after_success(hass: HomeAssistant) -> None:
    """Test that adding a participant clears editing state."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": "hub",
            "name": "Test Hub",
            "horizon_hours": 24,
            "period_minutes": 30,
            "optimizer": "highs",
            "participants": {},
        },
    )
    config_entry.add_to_hass(hass)

    flow = HubOptionsFlow()
    flow.hass = hass
    flow._config_entry = config_entry

    # Simulate stale editing state
    flow._editing_participant = {"name_value": "Stale"}

    # Add a new battery
    await flow.async_step_add_participant({"participant_type": "battery"})

    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        result = await flow.async_step_configure_battery(
            {
                "name_value": "New Battery",
                "capacity_value": 10.0,
                "initial_charge_percentage_value": "sensor.battery_soc",
                "min_charge_percentage_value": 20.0,
                "max_charge_percentage_value": 90.0,
                "max_charge_power_value": 5.0,
                "max_discharge_power_value": 5.0,
                "efficiency_value": 0.95,
            }
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    # Verify editing state was cleared
    assert flow._editing_participant is None


async def test_remove_participant_deletes_from_config(hass: HomeAssistant) -> None:
    """Test that removing a participant deletes it from configuration."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": "hub",
            "name": "Test Hub",
            "horizon_hours": 24,
            "period_minutes": 30,
            "optimizer": "highs",
            "participants": {
                "Battery 1": {
                    "type": "battery",
                    "name_value": "Battery 1",
                },
                "Battery 2": {
                    "type": "battery",
                    "name_value": "Battery 2",
                },
            },
        },
    )
    config_entry.add_to_hass(hass)

    flow = HubOptionsFlow()
    flow.hass = hass
    flow._config_entry = config_entry

    # Remove Battery 1
    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        result = await flow.async_step_remove_participant({"participant": "Battery 1"})

    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Verify Battery 1 was removed
    participants = config_entry.data["participants"]
    assert "Battery 1" not in participants
    assert "Battery 2" in participants


async def test_remove_participant_removes_orphaned_connections(hass: HomeAssistant) -> None:
    """Test that removing a participant also removes connections that reference it."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": "hub",
            "name": "Test Hub",
            "horizon_hours": 24,
            "period_minutes": 30,
            "optimizer": "highs",
            "participants": {
                "Battery": {
                    "type": "battery",
                    "name_value": "Battery",
                },
                "Grid": {
                    "type": "grid",
                    "name_value": "Grid",
                },
                "Net": {
                    "type": "node",
                    "name_value": "Net",
                },
                "Battery to Net": {
                    "type": "connection",
                    "name_value": "Battery to Net",
                    "source_value": "Battery",
                    "target_value": "Net",
                },
                "Grid to Net": {
                    "type": "connection",
                    "name_value": "Grid to Net",
                    "source_value": "Grid",
                    "target_value": "Net",
                },
            },
        },
    )
    config_entry.add_to_hass(hass)

    flow = HubOptionsFlow()
    flow.hass = hass
    flow._config_entry = config_entry

    # Remove Battery (should also remove "Battery to Net" connection)
    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        result = await flow.async_step_remove_participant({"participant": "Battery"})

    assert result["type"] == FlowResultType.CREATE_ENTRY

    participants = config_entry.data["participants"]
    # Verify Battery was removed
    assert "Battery" not in participants
    # Verify connection referencing Battery was removed
    assert "Battery to Net" not in participants
    # Verify other participants remain
    assert "Grid" in participants
    assert "Net" in participants
    assert "Grid to Net" in participants


async def test_remove_participant_removes_connections_by_target(hass: HomeAssistant) -> None:
    """Test that removing a participant removes connections that use it as target."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": "hub",
            "name": "Test Hub",
            "horizon_hours": 24,
            "period_minutes": 30,
            "optimizer": "highs",
            "participants": {
                "Battery": {
                    "type": "battery",
                    "name_value": "Battery",
                },
                "Net": {
                    "type": "node",
                    "name_value": "Net",
                },
                "Battery to Net": {
                    "type": "connection",
                    "name_value": "Battery to Net",
                    "source_value": "Battery",
                    "target_value": "Net",
                },
            },
        },
    )
    config_entry.add_to_hass(hass)

    flow = HubOptionsFlow()
    flow.hass = hass
    flow._config_entry = config_entry

    # Remove Net (should also remove connection targeting it)
    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        result = await flow.async_step_remove_participant({"participant": "Net"})

    assert result["type"] == FlowResultType.CREATE_ENTRY

    participants = config_entry.data["participants"]
    # Verify Net was removed
    assert "Net" not in participants
    # Verify connection targeting Net was removed
    assert "Battery to Net" not in participants
    # Verify Battery remains
    assert "Battery" in participants


async def test_remove_participant_clears_editing_state(hass: HomeAssistant) -> None:
    """Test that removing a participant clears any editing state."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": "hub",
            "name": "Test Hub",
            "horizon_hours": 24,
            "period_minutes": 30,
            "optimizer": "highs",
            "participants": {
                "Battery": {
                    "type": "battery",
                    "name_value": "Battery",
                },
            },
        },
    )
    config_entry.add_to_hass(hass)

    flow = HubOptionsFlow()
    flow.hass = hass
    flow._config_entry = config_entry

    # Simulate stale editing state
    flow._editing_participant = {"name_value": "Stale"}

    # Remove Battery
    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        result = await flow.async_step_remove_participant({"participant": "Battery"})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    # Verify editing state was cleared
    assert flow._editing_participant is None
