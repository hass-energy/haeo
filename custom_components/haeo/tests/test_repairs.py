"""Tests for the repairs module."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.issue_registry import IssueSeverity, async_get

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.repairs import (
    create_disconnected_network_issue,
    create_node_replaced_by_junction_issue,
    create_optimization_persistent_failure_issue,
    dismiss_disconnected_network_issue,
    dismiss_entry_issues,
    dismiss_optimization_failure_issue,
    sync_unavailable_input_issues,
)


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


async def test_optimization_failure_issue_translation_key(hass: HomeAssistant) -> None:
    """The optimization failure issue uses its translation key."""
    create_optimization_persistent_failure_issue(hass, "entry123", "error")
    issue = async_get(hass).async_get_issue(DOMAIN, "optimization_failure_entry123")
    assert issue is not None
    assert issue.translation_key == "optimization_failure"


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


async def test_dismiss_nonexistent_disconnected_network_issue(hass: HomeAssistant) -> None:
    """Test dismissing a disconnected network issue that doesn't exist."""
    entry_id = "test_entry_id"

    # Should not raise an error when dismissing non-existent issue
    dismiss_disconnected_network_issue(hass, entry_id)


async def test_dismiss_nonexistent_optimization_failure_issue(hass: HomeAssistant) -> None:
    """Test dismissing an optimization failure issue that doesn't exist."""
    entry_id = "test_entry_id"

    # Should not raise an error when dismissing non-existent issue
    dismiss_optimization_failure_issue(hass, entry_id)


async def test_create_node_replaced_by_junction_issue(hass: HomeAssistant) -> None:
    """The issue for a node replaced by a junction persists until the user ignores it."""
    create_node_replaced_by_junction_issue(hass, "entry123", "Switchboard")

    issue = async_get(hass).async_get_issue(DOMAIN, "node_replaced_by_junction_entry123_Switchboard")
    assert issue is not None
    assert issue.translation_key == "node_replaced_by_junction"
    assert issue.is_persistent
    assert not issue.is_fixable


async def test_dismiss_entry_issues_only_removes_that_entry(hass: HomeAssistant) -> None:
    """Dismissing an entry's issues leaves other entries' issues in place."""
    create_node_replaced_by_junction_issue(hass, "entry123", "Switchboard")
    create_disconnected_network_issue(hass, "entry123", [{"Battery"}, {"Grid"}])
    create_node_replaced_by_junction_issue(hass, "entry456", "Switchboard")

    dismiss_entry_issues(hass, "entry123")

    assert list(async_get(hass).issues) == [(DOMAIN, "node_replaced_by_junction_entry456_Switchboard")]


async def test_sync_unavailable_input_issues_raises_and_dismisses(hass: HomeAssistant) -> None:
    """Each unavailable input gets an issue naming its sensors, and recovered inputs lose theirs."""
    sync_unavailable_input_issues(
        hass,
        "entry123",
        {
            ("EV Charger", ("schedule", "energy_meter")): ("sensor.ev_energy",),
            ("Grid", ("pricing", "price_source_target")): ("sensor.price_a", "sensor.price_b"),
        },
    )
    sync_unavailable_input_issues(hass, "entry456", {("Grid", ("pricing", "price_source_target")): ("sensor.x",)})

    meter = async_get(hass).async_get_issue(DOMAIN, "unavailable_input_entry123_EV Charger_schedule.energy_meter")
    assert meter is not None
    assert meter.translation_key == "unavailable_input"
    assert meter.severity == IssueSeverity.ERROR
    assert meter.translation_placeholders == {
        "element": "EV Charger",
        "field": "schedule.energy_meter",
        "entities": "sensor.ev_energy",
    }

    sync_unavailable_input_issues(
        hass, "entry123", {("Grid", ("pricing", "price_source_target")): ("sensor.price_a", "sensor.price_b")}
    )

    assert sorted(issue_id for _, issue_id in async_get(hass).issues) == [
        "unavailable_input_entry123_Grid_pricing.price_source_target",
        "unavailable_input_entry456_Grid_pricing.price_source_target",
    ]
