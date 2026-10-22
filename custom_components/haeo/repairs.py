"""Repair helper for HAEO integration."""

from collections.abc import Collection, Mapping, Sequence
from functools import partial
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final

from homeassistant import data_entry_flow
from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue, async_delete_issue

from .const import DOMAIN

if TYPE_CHECKING:
    from .input_stores import InputStoreKey

_LOGGER = logging.getLogger(__name__)


# Issue data key holding the path of the diagnostics saved when the issue was raised
ISSUE_DIAGNOSTICS: Final = "diagnostics"


class FailureResolvedFlow(ConfirmRepairFlow):
    """Resolve an impossible or relaxed plan's issue, deleting the diagnostics saved for it."""

    async def async_step_confirm(self, user_input: dict[str, str] | None = None) -> data_entry_flow.FlowResult:
        """Delete the saved diagnostics once the user confirms the issue resolved."""
        if user_input is not None:
            await async_delete_issue_diagnostics(self.hass, self.data)
        return await super().async_step_confirm(user_input)


async def async_create_fix_flow(
    hass: HomeAssistant,  # noqa: ARG001 (signature required by the repairs platform)
    issue_id: str,  # noqa: ARG001 (signature required by the repairs platform)
    data: Mapping[str, str | int | float | None] | None,  # noqa: ARG001 (signature required by the repairs platform)
) -> RepairsFlow:
    """Return a flow that resolves a fixable issue once the user confirms it.

    Only the issues for impossible and relaxed plans are fixable. Their cause can
    come and go between optimizations, so they stay until the user resolves them,
    while the others clear themselves once their cause is gone.
    """
    return FailureResolvedFlow()


async def async_delete_issue_diagnostics(
    hass: HomeAssistant, data: Mapping[str, str | int | float | None] | None
) -> None:
    """Delete the diagnostics file an issue's data names, keeping to HAEO's diagnostics folder.

    The file lives only as long as its issue, so failures cannot fill the disk.
    """
    path = (data or {}).get(ISSUE_DIAGNOSTICS)
    if not isinstance(path, str):
        return
    saved = Path(path)
    if saved.parent != Path(hass.config.path("haeo", "diagnostics")):
        _LOGGER.warning("Not deleting diagnostics outside the HAEO diagnostics folder: %s", saved)
        return
    await hass.async_add_executor_job(partial(saved.unlink, missing_ok=True))


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


def create_horizon_tiers_replaced_issue(hass: HomeAssistant, entry_id: str, hub_name: str, days: int) -> None:
    """Create a repair issue for a hub whose custom horizon tiers were replaced by a preset of ``days`` days."""
    async_create_issue(
        hass,
        DOMAIN,
        f"horizon_tiers_replaced_{entry_id}",
        is_fixable=False,
        is_persistent=True,
        severity=IssueSeverity.WARNING,
        translation_key="horizon_tiers_replaced",
        translation_placeholders={"hub_name": hub_name, "days": str(days)},
    )


async def async_dismiss_entry_issues(hass: HomeAssistant, entry_id: str) -> None:
    """Dismiss every repair issue raised for a config entry, with the diagnostics saved for them."""
    for (domain, issue_id), issue in list(ir.async_get(hass).issues.items()):
        if domain == DOMAIN and entry_id in issue_id:
            await async_delete_issue_diagnostics(hass, issue.data)
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


def create_setup_failed_issue(hass: HomeAssistant, entry_id: str, error: str) -> None:
    """Raise a repair issue for a setup that failed unexpectedly and will be retried."""
    async_create_issue(
        hass,
        DOMAIN,
        f"setup_failed_{entry_id}",
        is_fixable=False,
        is_persistent=False,
        severity=IssueSeverity.ERROR,
        translation_key="setup_failed",
        translation_placeholders={"error": error},
    )


def dismiss_setup_failed_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Dismiss the setup failure issue once setup succeeds."""
    async_delete_issue(hass, DOMAIN, f"setup_failed_{entry_id}")


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


# Where a user reports an issue, with the diagnostics saved when it was raised
ISSUE_TRACKER_URL = "https://github.com/hass-energy/haeo/issues"


def optimization_infeasible_issue_raised(hass: HomeAssistant, entry_id: str) -> bool:
    """Return whether an impossible plan's issue is waiting for the user to resolve it."""
    return ir.async_get(hass).async_get_issue(DOMAIN, f"optimization_infeasible_{entry_id}") is not None


def optimization_relaxed_issue_raised(hass: HomeAssistant, entry_id: str) -> bool:
    """Return whether a relaxed plan's issue is waiting for the user to resolve it."""
    return ir.async_get(hass).async_get_issue(DOMAIN, f"optimization_relaxed_{entry_id}") is not None


def create_optimization_infeasible_issue(
    hass: HomeAssistant, entry_id: str, translation_key: str, placeholders: Mapping[str, str], diagnostics: str
) -> None:
    """Create a repair issue naming the elements whose constraints leave no feasible plan.

    The issue stays until the user marks it resolved, even once a later plan is
    found, so an intermittent impossible forecast cannot raise and clear it before
    anyone sees it.
    """
    async_create_issue(
        hass,
        DOMAIN,
        f"optimization_infeasible_{entry_id}",
        is_fixable=True,
        is_persistent=True,
        severity=IssueSeverity.ERROR,
        translation_key=translation_key,
        translation_placeholders={**placeholders, ISSUE_DIAGNOSTICS: diagnostics},
        learn_more_url=ISSUE_TRACKER_URL,
        data={ISSUE_DIAGNOSTICS: diagnostics},
    )


def create_optimization_relaxed_issue(
    hass: HomeAssistant, entry_id: str, placeholders: Mapping[str, str], diagnostics: str
) -> None:
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
        translation_placeholders={**placeholders, ISSUE_DIAGNOSTICS: diagnostics},
        learn_more_url=ISSUE_TRACKER_URL,
        data={ISSUE_DIAGNOSTICS: diagnostics},
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


def sync_mixed_price_currencies_issue(hass: HomeAssistant, entry_id: str, sources: Mapping[str, Sequence[str]]) -> None:
    """Raise a repair issue when price sources report more than one currency, and dismiss it otherwise.

    Keys are currencies and values are the source entities reporting prices in them.
    """
    issue_id = f"mixed_price_currencies_{entry_id}"
    if len(sources) < 2:  # noqa: PLR2004 (one currency is consistent)
        async_delete_issue(hass, DOMAIN, issue_id)
        return
    async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        is_persistent=False,
        severity=IssueSeverity.WARNING,
        translation_key="mixed_price_currencies",
        translation_placeholders={
            "currencies": "\n".join(
                f"- {currency}: {', '.join(sorted(entities))}" for currency, entities in sorted(sources.items())
            ),
        },
    )


def _unavailable_input_issue_prefix(entry_id: str) -> str:
    return f"unavailable_input_{entry_id}_"


def sync_unavailable_input_issues(
    hass: HomeAssistant,
    entry_id: str,
    unavailable: Mapping["InputStoreKey", Sequence[str]],
) -> None:
    """Raise a repair issue for each unavailable input and dismiss those that recovered.

    Keys are (element name, field path) and values are the source entities
    with no reading. An input whose sources all have readings but still
    cannot load names every source it reads.
    """
    prefix = _unavailable_input_issue_prefix(entry_id)
    wanted = {
        f"{prefix}{element_name}_{'.'.join(field_path)}": (element_name, field_path, entities)
        for (element_name, field_path), entities in unavailable.items()
    }

    for domain, issue_id in list(ir.async_get(hass).issues):
        if domain == DOMAIN and issue_id.startswith(prefix) and issue_id not in wanted:
            async_delete_issue(hass, DOMAIN, issue_id)

    for issue_id, (element_name, field_path, entities) in wanted.items():
        async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            is_persistent=False,
            severity=IssueSeverity.ERROR,
            translation_key="unavailable_input",
            translation_placeholders={
                "element": element_name,
                "field": ".".join(field_path),
                "entities": ", ".join(entities),
            },
        )
