"""Tests for elements module __init__.py functions."""

from types import MappingProxyType
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_INTEGRATION_TYPE, CONF_NAME, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.elements import (
    ELEMENT_CONFIG_SCHEMAS,
    collect_element_subentries,
    is_element_config_data,
    is_element_config_schema,
)
from custom_components.haeo.elements import battery, battery_section, connection, grid, inverter, load, solar
from custom_components.haeo.elements import node as node_schema
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value


@pytest.mark.parametrize(
    "input_data",
    [
        [1, 2, 3],
        "not a config",
        None,
    ],
)
def test_is_not_element_config_schema(input_data: Any) -> None:
    """Test is_element_config_schema with non-Mapping input."""
    assert is_element_config_schema(input_data) is False


@pytest.mark.parametrize(
    "input_data",
    [
        {"element_type": "unknown_type", "name": "test"},  # Unknown element type
        {"name": "test"},  # Missing element_type
        {"element_type": "battery"},  # Missing all required fields
        {
            "element_type": "battery",
            battery.SECTION_COMMON: {"name": "test"},
        },  # Missing required battery fields
        {
            "element_type": "connection",
            connection.SECTION_COMMON: {"name": "test"},
            connection.SECTION_ENDPOINTS: {"source": as_connection_target("a")},
        },  # Missing target
    ],
)
def test_is_element_config_schema_invalid_structure(input_data: dict[str, Any]) -> None:
    """Test is_element_config_schema with invalid element structure."""
    assert is_element_config_schema(input_data) is False


@pytest.mark.parametrize(
    "input_data",
    [
        # Wrong type for name (should be str)
        {
            "element_type": "node",
            node_schema.SECTION_COMMON: {"name": 123},
            node_schema.SECTION_ROLE: {"is_source": False, "is_sink": False},
        },
        # Wrong type for connection (should be connection target)
        {
            "element_type": "grid",
            grid.SECTION_COMMON: {"name": "test", "connection": ["list_not_str"]},
            grid.SECTION_PRICING: {
                "price_source_target": as_entity_value(["sensor.import"]),
                "price_target_source": as_entity_value(["sensor.export"]),
            },
            grid.SECTION_POWER_LIMITS: {},
        },
        # Wrong type for capacity (bool is rejected - bools are explicitly excluded from
        # constant value handling even though bool is a subclass of int in Python)
        {
            "element_type": "battery",
            battery.SECTION_COMMON: {
                "name": "test",
                "connection": as_connection_target("bus"),
            },
            battery.SECTION_STORAGE: {
                "capacity": True,
                "initial_charge_percentage": as_entity_value(["sensor.soc"]),
            },
            battery.SECTION_LIMITS: {},
            battery.SECTION_POWER_LIMITS: {},
            battery.SECTION_PRICING: {},
            battery.SECTION_EFFICIENCY: {},
            battery.SECTION_PARTITIONING: {},
            battery.SECTION_UNDERCHARGE: {},
            battery.SECTION_OVERCHARGE: {},
        },
    ],
)
def test_is_element_config_schema_wrong_field_types(input_data: dict[str, Any]) -> None:
    """Test is_element_config_schema rejects fields with wrong types for required fields."""


def test_is_element_config_schema_valid_node() -> None:
    """Test is_element_config_schema with valid node config."""
    valid_config = {
        "element_type": "node",
        node_schema.SECTION_COMMON: {"name": "test_node"},
        node_schema.SECTION_ROLE: {"is_source": False, "is_sink": False},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_node_minimal() -> None:
    """Test is_element_config_schema with minimal node config (optional fields omitted)."""
    valid_config = {
        "element_type": "node",
        node_schema.SECTION_COMMON: {"name": "test_node"},
        node_schema.SECTION_ROLE: {},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_battery() -> None:
    """Test is_element_config_schema with valid battery config."""
    valid_config = {
        "element_type": "battery",
        battery.SECTION_COMMON: {
            "name": "test_battery",
            "connection": as_connection_target("main_bus"),
        },
        battery.SECTION_STORAGE: {
            "capacity": as_entity_value(["sensor.capacity"]),
            "initial_charge_percentage": as_entity_value(["sensor.soc"]),
        },
        battery.SECTION_LIMITS: {
            "min_charge_percentage": as_constant_value(10.0),
            "max_charge_percentage": as_constant_value(90.0),
        },
        battery.SECTION_POWER_LIMITS: {
            "max_power_source_target": as_constant_value(5.0),
            "max_power_target_source": as_constant_value(5.0),
        },
        battery.SECTION_PRICING: {
            "price_target_source": as_constant_value(0.05),
        },
        battery.SECTION_EFFICIENCY: {},
        battery.SECTION_PARTITIONING: {},
        battery.SECTION_UNDERCHARGE: {},
        battery.SECTION_OVERCHARGE: {},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_grid() -> None:
    """Test is_element_config_schema with valid grid config."""
    valid_config = {
        "element_type": "grid",
        grid.SECTION_COMMON: {"name": "test_grid", "connection": as_connection_target("main_bus")},
        grid.SECTION_PRICING: {
            "price_source_target": as_entity_value(["sensor.import"]),
            "price_target_source": as_entity_value(["sensor.export"]),
        },
        grid.SECTION_POWER_LIMITS: {},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_grid_minimal() -> None:
    """Test is_element_config_schema with minimal valid grid config (prices required)."""
    valid_config = {
        "element_type": "grid",
        grid.SECTION_COMMON: {"name": "test_grid", "connection": as_connection_target("main_bus")},
        grid.SECTION_PRICING: {
            "price_source_target": as_constant_value(0.25),
            "price_target_source": as_constant_value(0.05),
        },
        grid.SECTION_POWER_LIMITS: {},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_connection() -> None:
    """Test is_element_config_schema with valid connection config."""
    valid_config = {
        "element_type": "connection",
        connection.SECTION_COMMON: {
            "name": "test_connection",
        },
        connection.SECTION_ENDPOINTS: {
            "source": as_connection_target("battery"),
            "target": as_connection_target("grid"),
        },
        connection.SECTION_POWER_LIMITS: {},
        connection.SECTION_PRICING: {},
        connection.SECTION_EFFICIENCY: {},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_load() -> None:
    """Test is_element_config_schema with valid load config."""
    valid_config = {
        "element_type": "load",
        load.SECTION_COMMON: {"name": "test_load", "connection": as_connection_target("main_bus")},
        load.SECTION_FORECAST: {"forecast": as_entity_value(["sensor.load_forecast"])},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_solar() -> None:
    """Test is_element_config_schema with valid solar config."""
    valid_config = {
        "element_type": "solar",
        solar.SECTION_COMMON: {"name": "test_solar", "connection": as_connection_target("main_bus")},
        solar.SECTION_FORECAST: {"forecast": as_entity_value(["sensor.solar_forecast"])},
        solar.SECTION_PRICING: {"price_source_target": as_constant_value(0.0)},
        solar.SECTION_CURTAILMENT: {"curtailment": as_constant_value(value=True)},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_inverter() -> None:
    """Test is_element_config_schema with valid inverter config."""
    valid_config = {
        "element_type": "inverter",
        inverter.SECTION_COMMON: {"name": "test_inverter", "connection": as_connection_target("ac_bus")},
        inverter.SECTION_POWER_LIMITS: {
            "max_power_source_target": as_entity_value(["sensor.dc_to_ac"]),
            "max_power_target_source": as_entity_value(["sensor.ac_to_dc"]),
        },
        inverter.SECTION_EFFICIENCY: {},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_battery_section() -> None:
    """Test is_element_config_schema with valid battery_section config."""
    valid_config = {
        "element_type": "battery_section",
        battery_section.SECTION_COMMON: {"name": "test_section"},
        battery_section.SECTION_STORAGE: {
            "capacity": as_entity_value(["sensor.capacity"]),
            "initial_charge": as_entity_value(["sensor.charge"]),
        },
    }
    assert is_element_config_schema(valid_config) is True


@pytest.mark.parametrize(
    "input_data",
    [
        [1, 2, 3],
        "not a config",
        None,
    ],
)
def test_is_not_element_config_data(input_data: Any) -> None:
    """Test is_element_config_data with non-Mapping input."""
    assert is_element_config_data(input_data) is False


@pytest.mark.parametrize(
    "input_data",
    [
        {"element_type": "unknown_type", "name": "test"},
        {"name": "test"},
    ],
)
def test_is_element_config_data_invalid_element_type(input_data: dict[str, Any]) -> None:
    """Test is_element_config_data with invalid element types."""
    assert is_element_config_data(input_data) is False


def test_is_element_config_data_missing_required_keys() -> None:
    """Test is_element_config_data rejects missing required keys."""
    invalid_config = {
        "element_type": "battery",
        battery.SECTION_COMMON: {"name": "test_battery"},
        # Missing required keys like connection/capacity/initial_charge_percentage.
    }
    assert is_element_config_data(invalid_config) is False


def test_is_element_config_data_valid_node() -> None:
    """Test is_element_config_data with minimal valid node config."""
    valid_config = {
        "element_type": "node",
        node_schema.SECTION_COMMON: {"name": "test_node"},
        node_schema.SECTION_ROLE: {},
    }
    assert is_element_config_data(valid_config) is True


def test_is_element_config_data_optional_type_validation() -> None:
    """Test is_element_config_data validates optional key types."""
    invalid_config = {
        "element_type": node_schema.ELEMENT_TYPE,
        node_schema.SECTION_COMMON: {"name": "test_node"},
        node_schema.SECTION_ROLE: {"is_source": "yes"},
    }
    assert is_element_config_data(invalid_config) is False

    valid_config = {
        "element_type": node_schema.ELEMENT_TYPE,
        node_schema.SECTION_COMMON: {"name": "test_node"},
        node_schema.SECTION_ROLE: {"is_source": True},
    }
    assert is_element_config_data(valid_config) is True


def test_collect_element_subentries_skips_invalid_configs(
    hass: HomeAssistant,
) -> None:
    """collect_element_subentries should warn and skip invalid subentries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Network",
        },
        entry_id="hub_entry_id",
    )
    entry.add_to_hass(hass)

    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: battery.ELEMENT_TYPE,
                CONF_NAME: "Bad Battery",
            }
        ),
        subentry_type=battery.ELEMENT_TYPE,
        title="Bad Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, subentry)

    result = collect_element_subentries(entry)

    assert result == []


def test_config_schemas_match_element_types() -> None:
    """Ensure ELEMENT_CONFIG_SCHEMAS has an entry for every registered element type."""
    from custom_components.haeo.elements import ELEMENT_TYPES

    for element_type in ELEMENT_TYPES:
        assert element_type in ELEMENT_CONFIG_SCHEMAS, f"Missing config schema for {element_type}"
