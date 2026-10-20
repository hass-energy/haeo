"""Repair helper for HAEO integration."""

from collections.abc import Collection, Mapping, Sequence
import logging

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue, async_delete_issue

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_create_fix_flow(
    hass: HomeAssistant,  # noqa: ARG001 (signature required by the repairs platform)
    issue_id: str,  # noqa: ARG001 (signature required by the repairs platform)
    data: Mapping[str, str | int | float | None] | None,  # noqa: ARG001 (signature required by the repairs platform)
) -> RepairsFlow:
    """Return a flow that resolves a fixable issue once the user confirms it.

    Only a relaxed plan's issue is fixable: the others clear themselves once their
    cause is gone, while a relaxed plan stays a failure until the user resolves it.
    """
    return ConfirmRepairFlow()


def _summarize_components(components: Sequence[Collection[str]]) -> str:
    """Create a human-readable summary of disconnected components."""

    lines: list[str] = []
    for index, component in enumerate(components, start=1):
        members = ", ".join(sorted(component)) if component else "(no entities)"
        lines.append(f"{index}) {members}")
    return "\n".join(lines)


def create_disconnected_network_issue(
    hass: HomeAssistant,
    entry_id: str,
    components: Sequence[Collection[str]],
) -> None:
    """Create a repair issue for disconnected network components."""

    num_components = len(components)
    component_summary = _summarize_components(components)
    issue_id = f"disconnected_network_{entry_id}"

    async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        is_persistent=True,
        severity=IssueSeverity.WARNING,
        translation_key="disconnected_network",
        translation_placeholders={
            "num_components": str(num_components),
            "component_summary": component_summary,
        },
    )

    _LOGGER.warning(
        "Created repair issue for disconnected network on entry %s (%s components)",
        entry_id,
        num_components,
    )


def create_node_replaced_by_junction_issue(hass: HomeAssistant, entry_id: str, element_name: str) -> None:
    """Create a repair issue for a node whose source or sink role was removed by becoming a junction."""
    async_create_issue(
        hass,
        DOMAIN,
        f"node_replaced_by_junction_{entry_id}_{element_name}",
        is_fixable=False,
        is_persistent=True,
        severity=IssueSeverity.WARNING,
        translation_key="node_replaced_by_junction",
        translation_placeholders={"element_name": element_name},
    )


def dismiss_entry_issues(hass: HomeAssistant, entry_id: str) -> None:
    """Dismiss every repair issue raised for a config entry."""
    for domain, issue_id in list(ir.async_get(hass).issues):
        if domain == DOMAIN and entry_id in issue_id:
            async_delete_issue(hass, DOMAIN, issue_id)


def dismiss_disconnected_network_issue(
    hass: HomeAssistant,
    entry_id: str,
) -> None:
    """Dismiss a repair issue for disconnected network components."""

    issue_id = f"disconnected_network_{entry_id}"
    async_delete_issue(hass, DOMAIN, issue_id)
    _LOGGER.debug("Dismissed disconnected network issue for entry %s", entry_id)


def create_invalid_connection_endpoints_issue(
    hass: HomeAssistant,
    entry_id: str,
    invalid_endpoints: Mapping[str, Sequence[str]],
) -> None:
    """Create a repair issue for elements connected directly to closed endpoints."""

    connection_summary = "\n".join(
        f"{element} → {', '.join(endpoints)}" for element, endpoints in sorted(invalid_endpoints.items())
    )
    issue_id = f"invalid_connection_endpoints_{entry_id}"

    async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        is_persistent=True,
        severity=IssueSeverity.WARNING,
        translation_key="invalid_connection_endpoints",
        translation_placeholders={"connection_summary": connection_summary},
    )

    _LOGGER.warning(
        "Created repair issue for invalid connection endpoints on entry %s: %s",
        entry_id,
        connection_summary.replace("\n", "; "),
    )


def dismiss_invalid_connection_endpoints_issue(
    hass: HomeAssistant,
    entry_id: str,
) -> None:
    """Dismiss the invalid connection endpoints repair issue."""

    issue_id = f"invalid_connection_endpoints_{entry_id}"
    async_delete_issue(hass, DOMAIN, issue_id)
    _LOGGER.debug("Dismissed invalid connection endpoints issue for entry %s", entry_id)


def create_optimization_persistent_failure_issue(
    hass: HomeAssistant,
    entry_id: str,
    error_message: str,
) -> None:
    """Create a repair issue for persistent optimization failures.

    Args:
        hass: Home Assistant instance
        entry_id: Config entry ID
        error_message: The error message from the optimization failure

    """
    issue_id = f"optimization_failure_{entry_id}"

    async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        is_persistent=False,
        severity=IssueSeverity.ERROR,
        translation_key="optimization_failure",
        translation_placeholders={
            "error_message": error_message,
        },
    )

    _LOGGER.warning(
        "Created repair issue for persistent optimization failure: %s",
        error_message,
    )


def dismiss_optimization_failure_issue(
    hass: HomeAssistant,
    entry_id: str,
) -> None:
    """Dismiss optimization failure issue when optimization succeeds.

    Args:
        hass: Home Assistant instance
        entry_id: Config entry ID

    """
    issue_id = f"optimization_failure_{entry_id}"
    async_delete_issue(hass, DOMAIN, issue_id)
    _LOGGER.debug("Dismissed optimization failure repair issue")


def create_optimization_infeasible_issue(
    hass: HomeAssistant, entry_id: str, translation_key: str, placeholders: Mapping[str, str]
) -> None:
    """Create a repair issue naming the elements whose constraints leave no feasible plan."""
    async_create_issue(
        hass,
        DOMAIN,
        f"optimization_infeasible_{entry_id}",
        is_fixable=False,
        is_persistent=False,
        severity=IssueSeverity.ERROR,
        translation_key=translation_key,
        translation_placeholders=dict(placeholders),
    )


def dismiss_optimization_infeasible_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Dismiss the infeasible plan issue once a plan is found."""
    async_delete_issue(hass, DOMAIN, f"optimization_infeasible_{entry_id}")


def create_optimization_relaxed_issue(hass: HomeAssistant, entry_id: str, placeholders: Mapping[str, str]) -> None:
    """Create a repair issue naming where a plan had to relax constraints.

    A relaxed plan is still a failure, so the issue stays until the user marks it
    resolved, even once later plans meet every constraint. Intermittent relaxations
    then cannot raise and clear it before anyone sees it.
    """
    async_create_issue(
        hass,
        DOMAIN,
        f"optimization_relaxed_{entry_id}",
        is_fixable=True,
        is_persistent=True,
        severity=IssueSeverity.WARNING,
        translation_key="optimization_relaxed",
        translation_placeholders=dict(placeholders),
    )


def _calendar_event_values_issue_id(entry_id: str, element_name: str, field_path: Sequence[str]) -> str:
    return f"calendar_event_values_{entry_id}_{element_name}_{'.'.join(field_path)}"


def create_calendar_event_values_issue(
    hass: HomeAssistant,
    entry_id: str,
    element_name: str,
    field_path: Sequence[str],
    *,
    calendars: Sequence[str],
    events: Sequence[str],
    unit: str,
) -> None:
    """Create a repair issue for calendar events whose values an input ignores."""
    async_create_issue(
        hass,
        DOMAIN,
        _calendar_event_values_issue_id(entry_id, element_name, field_path),
        is_fixable=False,
        is_persistent=False,
        severity=IssueSeverity.WARNING,
        translation_key="calendar_event_values_ignored",
        translation_placeholders={
            "element": element_name,
            "field": ".".join(field_path),
            "calendars": ", ".join(calendars),
            "events": "\n".join(f"- {event}" for event in events),
            "unit": unit,
        },
    )


def dismiss_calendar_event_values_issue(
    hass: HomeAssistant, entry_id: str, element_name: str, field_path: Sequence[str]
) -> None:
    """Dismiss the repair issue for an input's calendar events, if raised."""
    async_delete_issue(hass, DOMAIN, _calendar_event_values_issue_id(entry_id, element_name, field_path))
