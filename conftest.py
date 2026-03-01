"""Test configuration and fixtures."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib import import_module
from logging import config as logging_config_module
from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.const import CONF_ADVANCED_MODE, CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON

# Enable custom component for testing
pytest_plugins = ["pytest_homeassistant_custom_component"]


@dataclass(frozen=True, slots=True)
class FlowTestCase:
    """Container for flow test case data."""

    description: str
    config: dict[str, Any]
    error: str | None = None
    mode_input: dict[str, Any] | None = None  # For two-step flows (mode selection input)


@dataclass(frozen=True, slots=True)
class ElementTestData:
    """Aggregated valid and invalid flow test cases for an element type."""

    valid: tuple[FlowTestCase, ...]
    invalid: tuple[FlowTestCase, ...]


@dataclass(frozen=True, slots=True)
class FakeEntityState:
    """Minimal entity state used by core loader tests."""

    entity_id: str
    state: str
    attributes: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        """Return dictionary representation compatible with EntityState."""
        return {
            "entity_id": self.entity_id,
            "state": self.state,
            "attributes": dict(self.attributes),
        }


class FakeStateMachine:
    """State machine test double with deterministic lookups."""

    def __init__(self, states: Mapping[str, FakeEntityState]) -> None:
        """Initialize with preloaded states keyed by entity ID."""
        self._states = dict(states)

    def get(self, entity_id: str) -> FakeEntityState | None:
        """Return state for entity when present."""
        return self._states.get(entity_id)


def _load_flow_cases(cases: Iterable[dict[str, Any]], *, include_error: bool) -> tuple[FlowTestCase, ...]:
    """Convert raw module test data into structured cases."""

    structured_cases: list[FlowTestCase] = []
    for case in cases:
        description = case.get("description", "")
        config = case.get("config", {})
        error = case.get("error") if include_error else None
        mode_input = case.get("mode_input")
        structured_cases.append(
            FlowTestCase(
                description=description,
                config=dict(config),
                error=error,
                mode_input=dict(mode_input) if mode_input else None,
            )
        )
    return tuple(structured_cases)


@pytest.fixture
def hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a minimal hub entry for flow testing.

    Only includes fields required for element flow tests. Tier configuration
    and other hub-specific settings are not needed for testing element flows.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {CONF_NAME: "Test Hub"},
            HUB_SECTION_ADVANCED: {CONF_ADVANCED_MODE: True},
        },
        entry_id="test_hub_id",
    )
    entry.add_to_hass(hass)
    return entry


def add_participant(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    name: str,
    element_type: str = "node",
) -> ConfigSubentry:
    """Add a participant subentry for connection endpoints."""
    data = MappingProxyType({CONF_ELEMENT_TYPE: element_type, CONF_NAME: name})
    subentry = ConfigSubentry(
        data=data,
        subentry_type=element_type,
        title=name,
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)
    return subentry


@pytest.fixture(scope="session")
def element_test_data() -> dict[str, ElementTestData]:
    """Load dynamic element test data for all element types."""

    data: dict[str, ElementTestData] = {}

    for element_type in ELEMENT_TYPES:
        module_name = f"custom_components.haeo.flows.tests.test_data.{element_type}"
        module = import_module(module_name)

        valid_cases = getattr(module, "VALID_DATA", [])
        invalid_cases = getattr(module, "INVALID_DATA", [])

        data[element_type] = ElementTestData(
            valid=_load_flow_cases(valid_cases, include_error=False),
            invalid=_load_flow_cases(invalid_cases, include_error=True),
        )

    return data


@pytest.fixture(autouse=True, scope="session")
def configure_logging() -> None:
    """Configure logging to suppress verbose Home Assistant DEBUG messages during tests."""
    # Set up logging configuration to reduce noise during tests
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "brief": {"format": "%(levelname)s: %(name)s: %(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "brief",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            # Suppress verbose DEBUG logs from Home Assistant core
            "homeassistant.core": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            # Keep our custom component logs at INFO level for debugging
            "custom_components.haeo": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console"],
        },
    }

    # Apply the logging configuration
    logging_config_module.dictConfig(logging_config)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request: pytest.FixtureRequest) -> bool:
    """Enable loading custom integrations in all tests.

    Skip for guide tests which use their own HA instance without
    the pytest-homeassistant-custom-component fixtures.
    """
    # Skip for guide tests - they don't use the hass fixture
    if "guide" in (mark.name for mark in request.node.iter_markers()):
        return True

    # For non-guide tests, request the enable_custom_integrations fixture
    # which depends on the hass fixture
    enable_custom_integrations = request.getfixturevalue("enable_custom_integrations")
    return enable_custom_integrations is None
