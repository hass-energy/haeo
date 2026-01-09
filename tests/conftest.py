"""Test configuration and fixtures."""

from collections.abc import Iterable
from dataclasses import dataclass
from importlib import import_module
from logging import config as logging_config_module
from typing import Any

import pytest

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.elements import ELEMENT_TYPES

# Enable custom component for testing
pytest_plugins = ["pytest_homeassistant_custom_component"]

# Entity ID for the configurable sentinel entity (domain.suggested_object_id)
TEST_CONFIGURABLE_ENTITY_ID = f"{DOMAIN}.configurable_entity"


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


@pytest.fixture(scope="session")
def element_test_data() -> dict[str, ElementTestData]:
    """Load dynamic element test data for all element types."""

    data: dict[str, ElementTestData] = {}

    for element_type in ELEMENT_TYPES:
        module_name = f"tests.flows.test_data.{element_type}"
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
def auto_enable_custom_integrations(enable_custom_integrations: None) -> bool:
    """Enable loading custom integrations in all tests."""
    return enable_custom_integrations is None
