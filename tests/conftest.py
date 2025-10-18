"""Test configuration and fixtures."""

from collections.abc import Iterable
from dataclasses import dataclass
from importlib import import_module
from logging import config as logging_config_module
from typing import Any, Literal

import pytest

from custom_components.haeo.const import ATTR_ENERGY, ATTR_POWER, ELEMENT_TYPE_NETWORK
from custom_components.haeo.elements import ELEMENT_TYPE_BATTERY, ELEMENT_TYPES
from custom_components.haeo.sensors.cost import HaeoCostSensor
from custom_components.haeo.sensors.energy import SENSOR_TYPE_ENERGY, HaeoEnergySensor
from custom_components.haeo.sensors.optimization import (
    SENSOR_TYPE_OPTIMIZATION_COST,
    SENSOR_TYPE_OPTIMIZATION_DURATION,
    SENSOR_TYPE_OPTIMIZATION_STATUS,
    HaeoOptimizationCostSensor,
    HaeoOptimizationDurationSensor,
    HaeoOptimizationStatusSensor,
)
from custom_components.haeo.sensors.power import SENSOR_TYPE_POWER, HaeoPowerSensor
from custom_components.haeo.sensors.soc import SENSOR_TYPE_SOC, HaeoSOCSensor

# Enable custom component for testing
pytest_plugins = ["pytest_homeassistant_custom_component"]


@dataclass(frozen=True, slots=True)
class FlowTestCase:
    """Container for flow test case data."""

    description: str
    config: dict[str, Any]
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ElementTestData:
    """Aggregated valid and invalid flow test cases for an element type."""

    valid: tuple[FlowTestCase, ...]
    invalid: tuple[FlowTestCase, ...]


@dataclass(frozen=True, slots=True)
class SensorTestData:
    """Metadata describing how to construct and validate a sensor instance."""

    cls: type[Any]
    category: Literal["element", "optimization"]
    translation_key: str
    name_suffix: str
    unique_suffix: str
    element_name: str
    element_type: str
    expect_native_value: bool = True
    requires_capacity: bool = False
    attribute_key: str | None = None


def _load_flow_cases(cases: Iterable[dict[str, Any]], *, include_error: bool) -> tuple[FlowTestCase, ...]:
    """Convert raw module test data into structured cases."""

    structured_cases: list[FlowTestCase] = []
    for case in cases:
        description = case.get("description", "")
        config = case.get("config", {})
        error = case.get("error") if include_error else None
        structured_cases.append(FlowTestCase(description=description, config=dict(config), error=error))
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


@pytest.fixture(scope="session")
def sensor_test_data() -> dict[str, SensorTestData]:
    """Provide structured sensor test metadata keyed by sensor translation key."""

    element_name = "test_battery"
    network_name = "network"

    return {
        SENSOR_TYPE_POWER: SensorTestData(
            cls=HaeoPowerSensor,
            category="element",
            translation_key=SENSOR_TYPE_POWER,
            name_suffix="Power",
            unique_suffix=f"{element_name}_{SENSOR_TYPE_POWER}",
            element_name=element_name,
            element_type=ELEMENT_TYPE_BATTERY,
            attribute_key=ATTR_POWER,
        ),
        SENSOR_TYPE_ENERGY: SensorTestData(
            cls=HaeoEnergySensor,
            category="element",
            translation_key=SENSOR_TYPE_ENERGY,
            name_suffix="Energy",
            unique_suffix=f"{element_name}_{SENSOR_TYPE_ENERGY}",
            element_name=element_name,
            element_type=ELEMENT_TYPE_BATTERY,
            attribute_key=ATTR_ENERGY,
        ),
        SENSOR_TYPE_SOC: SensorTestData(
            cls=HaeoSOCSensor,
            category="element",
            translation_key=SENSOR_TYPE_SOC,
            name_suffix="State of Charge",
            unique_suffix=f"{element_name}_state_of_charge",
            element_name=element_name,
            element_type=ELEMENT_TYPE_BATTERY,
            attribute_key=ATTR_ENERGY,
            requires_capacity=True,
        ),
        "element_cost": SensorTestData(
            cls=HaeoCostSensor,
            category="element",
            translation_key="cost",
            name_suffix="Cost",
            unique_suffix=f"{element_name}_cost",
            element_name=element_name,
            element_type=ELEMENT_TYPE_BATTERY,
            expect_native_value=False,
        ),
        SENSOR_TYPE_OPTIMIZATION_COST: SensorTestData(
            cls=HaeoOptimizationCostSensor,
            category="optimization",
            translation_key=SENSOR_TYPE_OPTIMIZATION_COST,
            name_suffix="Optimization Cost",
            unique_suffix=f"{network_name}_cost",
            element_name=network_name,
            element_type=ELEMENT_TYPE_NETWORK,
        ),
        SENSOR_TYPE_OPTIMIZATION_STATUS: SensorTestData(
            cls=HaeoOptimizationStatusSensor,
            category="optimization",
            translation_key=SENSOR_TYPE_OPTIMIZATION_STATUS,
            name_suffix="Optimization Status",
            unique_suffix="optimization_status",
            element_name=network_name,
            element_type=ELEMENT_TYPE_NETWORK,
        ),
        SENSOR_TYPE_OPTIMIZATION_DURATION: SensorTestData(
            cls=HaeoOptimizationDurationSensor,
            category="optimization",
            translation_key=SENSOR_TYPE_OPTIMIZATION_DURATION,
            name_suffix="Optimization Duration",
            unique_suffix="optimization_duration",
            element_name=network_name,
            element_type=ELEMENT_TYPE_NETWORK,
        ),
    }


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
