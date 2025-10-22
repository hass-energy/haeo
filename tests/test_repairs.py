"""Tests for the repairs module."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.issue_registry import IssueSeverity, async_get

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.repairs import (
    create_disconnected_network_issue,
    create_invalid_config_issue,
    create_missing_sensor_issue,
    create_optimization_persistent_failure_issue,
    dismiss_disconnected_network_issue,
    dismiss_missing_sensor_issue,
    dismiss_optimization_failure_issue,
)


async def test_create_missing_sensor_issue(hass: HomeAssistant) -> None:
    """Test creating a missing sensor repair issue."""
    element_name = "test_battery"
    sensor_entity_id = "sensor.test_power"

    create_missing_sensor_issue(hass, element_name, sensor_entity_id)

    # Verify issue was created
    issue_registry = async_get(hass)
    issue_id = f"missing_sensor_{element_name}_{sensor_entity_id.replace('.', '_')}"
    issue = issue_registry.async_get_issue(DOMAIN, issue_id)

    assert issue is not None
    assert issue.severity == IssueSeverity.WARNING
    assert not issue.is_fixable
    assert not issue.is_persistent


async def test_dismiss_missing_sensor_issue(hass: HomeAssistant) -> None:
    """Test dismissing a missing sensor repair issue."""
    element_name = "test_battery"
    sensor_entity_id = "sensor.test_power"

    # Create issue first
    create_missing_sensor_issue(hass, element_name, sensor_entity_id)

    # Verify it exists
    issue_registry = async_get(hass)
    issue_id = f"missing_sensor_{element_name}_{sensor_entity_id.replace('.', '_')}"
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is not None

    # Dismiss it
    dismiss_missing_sensor_issue(hass, element_name, sensor_entity_id)

    # Verify it's gone
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None


async def test_dismiss_missing_sensor_issue_not_exists(hass: HomeAssistant) -> None:
    """Test dismissing a non-existent issue doesn't raise error."""
    element_name = "test_battery"
    sensor_entity_id = "sensor.test_power"

    # Should not raise exception even if issue doesn't exist
    dismiss_missing_sensor_issue(hass, element_name, sensor_entity_id)


async def test_create_optimization_failure_issue(hass: HomeAssistant) -> None:
    """Test creating an optimization failure repair issue."""
    entry_id = "test_entry_123"
    error_message = "Solver failed to find solution"

    create_optimization_persistent_failure_issue(hass, entry_id, error_message)

    # Verify issue was created
    issue_registry = async_get(hass)
    issue_id = f"optimization_failure_{entry_id}"
    issue = issue_registry.async_get_issue(DOMAIN, issue_id)

    assert issue is not None
    assert issue.severity == IssueSeverity.ERROR
    assert not issue.is_fixable
    assert not issue.is_persistent


async def test_dismiss_optimization_failure_issue(hass: HomeAssistant) -> None:
    """Test dismissing an optimization failure repair issue."""
    entry_id = "test_entry_123"
    error_message = "Solver failed"

    # Create issue first
    create_optimization_persistent_failure_issue(hass, entry_id, error_message)

    # Verify it exists
    issue_registry = async_get(hass)
    issue_id = f"optimization_failure_{entry_id}"
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is not None

    # Dismiss it
    dismiss_optimization_failure_issue(hass, entry_id)

    # Verify it's gone
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None


async def test_dismiss_optimization_failure_issue_not_exists(hass: HomeAssistant) -> None:
    """Test dismissing a non-existent optimization issue doesn't raise error."""
    entry_id = "test_entry_123"

    # Should not raise exception even if issue doesn't exist
    dismiss_optimization_failure_issue(hass, entry_id)


async def test_create_invalid_config_issue(hass: HomeAssistant) -> None:
    """Test creating an invalid config repair issue."""
    element_name = "test_battery"
    config_problem = "Capacity must be greater than zero"

    create_invalid_config_issue(hass, element_name, config_problem)

    # Verify issue was created
    issue_registry = async_get(hass)
    issue_id = f"invalid_config_{element_name}"
    issue = issue_registry.async_get_issue(DOMAIN, issue_id)

    assert issue is not None
    assert issue.severity == IssueSeverity.ERROR
    assert issue.is_fixable
    assert issue.is_persistent


async def test_multiple_missing_sensor_issues(hass: HomeAssistant) -> None:
    """Test creating multiple missing sensor issues for different elements."""
    elements = [
        ("battery1", "sensor.battery1_power"),
        ("battery2", "sensor.battery2_power"),
        ("grid", "sensor.grid_power"),
    ]

    # Create issues for all elements
    for element_name, sensor_id in elements:
        create_missing_sensor_issue(hass, element_name, sensor_id)

    # Verify all were created
    issue_registry = async_get(hass)
    for element_name, sensor_id in elements:
        issue_id = f"missing_sensor_{element_name}_{sensor_id.replace('.', '_')}"
        assert issue_registry.async_get_issue(DOMAIN, issue_id) is not None


async def test_repair_issue_translation_keys(hass: HomeAssistant) -> None:
    """Test that repair issues use correct translation keys."""
    # Missing sensor issue
    create_missing_sensor_issue(hass, "battery", "sensor.power")
    issue_registry = async_get(hass)
    issue = issue_registry.async_get_issue(DOMAIN, "missing_sensor_battery_sensor_power")
    assert issue is not None
    assert issue.translation_key == "missing_sensor"

    # Optimization failure issue
    create_optimization_persistent_failure_issue(hass, "entry123", "error")
    issue = issue_registry.async_get_issue(DOMAIN, "optimization_failure_entry123")
    assert issue is not None
    assert issue.translation_key == "optimization_failure"

    # Invalid config issue
    create_invalid_config_issue(hass, "battery", "problem")
    issue = issue_registry.async_get_issue(DOMAIN, "invalid_config_battery")
    assert issue is not None
    assert issue.translation_key == "invalid_config"


async def test_create_disconnected_network_issue(hass: HomeAssistant) -> None:
    """Test creating disconnected network repair issue."""

    components = [{"Battery"}, {"Grid", "Load"}]
    entry_id = "entry123"

    create_disconnected_network_issue(hass, entry_id, components)

    issue_registry = async_get(hass)
    issue_id = f"disconnected_network_{entry_id}"
    issue = issue_registry.async_get_issue(DOMAIN, issue_id)

    assert issue is not None
    assert issue.severity == IssueSeverity.WARNING
    assert issue.is_fixable
    assert issue.is_persistent
    assert issue.translation_key == "disconnected_network"
    assert issue.translation_placeholders is not None
    assert issue.translation_placeholders.get("num_components") == "2"
    summary = issue.translation_placeholders.get("component_summary")
    assert summary is not None
    assert "1) Battery" in summary
    assert "2) Grid, Load" in summary


async def test_dismiss_disconnected_network_issue(hass: HomeAssistant) -> None:
    """Test dismissing disconnected network repair issue."""

    components = [{"Battery"}, {"Grid"}]
    entry_id = "entry123"

    create_disconnected_network_issue(hass, entry_id, components)

    issue_registry = async_get(hass)
    issue_id = f"disconnected_network_{entry_id}"
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is not None

    dismiss_disconnected_network_issue(hass, entry_id)

    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None
