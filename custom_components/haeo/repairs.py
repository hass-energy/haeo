"""Repair helper for HAEO integration."""

from collections.abc import Sequence
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue, async_delete_issue

from .const import DOMAIN
from .validation import format_component_summary

_LOGGER = logging.getLogger(__name__)


def create_missing_sensor_issue(
    hass: HomeAssistant,
    element_name: str,
    sensor_entity_id: str,
) -> None:
    """Create a repair issue for a missing sensor entity.

    Args:
        hass: Home Assistant instance
        element_name: Name of the element missing the sensor
        sensor_entity_id: The entity ID that is missing

    """
    issue_id = f"missing_sensor_{element_name}_{sensor_entity_id.replace('.', '_')}"

    async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        is_persistent=False,
        severity=IssueSeverity.WARNING,
        translation_key="missing_sensor",
        translation_placeholders={
            "element_name": element_name,
            "sensor_entity_id": sensor_entity_id,
        },
    )

    _LOGGER.info(
        "Created repair issue for missing sensor: %s on element %s",
        sensor_entity_id,
        element_name,
    )


def dismiss_missing_sensor_issue(
    hass: HomeAssistant,
    element_name: str,
    sensor_entity_id: str,
) -> None:
    """Dismiss a repair issue when the sensor becomes available.

    Args:
        hass: Home Assistant instance
        element_name: Name of the element
        sensor_entity_id: The entity ID that is now available

    """
    issue_id = f"missing_sensor_{element_name}_{sensor_entity_id.replace('.', '_')}"

    try:
        async_delete_issue(hass, DOMAIN, issue_id)
        _LOGGER.debug(
            "Dismissed repair issue for sensor: %s on element %s",
            sensor_entity_id,
            element_name,
        )
    except KeyError:
        # Issue doesn't exist, which is fine
        pass


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

    try:
        async_delete_issue(hass, DOMAIN, issue_id)
        _LOGGER.debug("Dismissed optimization failure repair issue")
    except KeyError:
        # Issue doesn't exist, which is fine
        pass


def create_invalid_config_issue(
    hass: HomeAssistant,
    element_name: str,
    config_problem: str,
) -> None:
    """Create a repair issue for invalid element configuration.

    Args:
        hass: Home Assistant instance
        element_name: Name of the element with invalid config
        config_problem: Description of the configuration problem

    """
    issue_id = f"invalid_config_{element_name}"

    async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=True,
        is_persistent=True,
        severity=IssueSeverity.ERROR,
        translation_key="invalid_config",
        translation_placeholders={
            "element_name": element_name,
            "config_problem": config_problem,
        },
    )

    _LOGGER.error(
        "Created repair issue for invalid configuration on element %s: %s",
        element_name,
        config_problem,
    )


def create_disconnected_network_issue(
    hass: HomeAssistant,
    entry_id: str,
    components: Sequence[set[str]],
) -> None:
    """Create a repair issue for disconnected network components."""

    issue_id = f"disconnected_network_{entry_id}"
    normalized_components = [tuple(sorted(component)) for component in components]
    issue_summary = format_component_summary(normalized_components)

    async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=True,
        is_persistent=True,
        severity=IssueSeverity.WARNING,
        translation_key="disconnected_network",
        translation_placeholders={
            "num_components": str(len(components)),
            "component_summary": issue_summary,
        },
    )

    _LOGGER.info(
        "Created repair issue for disconnected network on entry %s: %s",
        entry_id,
        format_component_summary(normalized_components, separator=" | ") or "no components",
    )


def dismiss_disconnected_network_issue(
    hass: HomeAssistant,
    entry_id: str,
) -> None:
    """Dismiss the disconnected network repair issue when connectivity is restored."""

    issue_id = f"disconnected_network_{entry_id}"

    try:
        async_delete_issue(hass, DOMAIN, issue_id)
        _LOGGER.debug("Dismissed disconnected network repair issue for entry %s", entry_id)
    except KeyError:
        pass
