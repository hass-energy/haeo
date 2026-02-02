"""Tests for elements module __init__.py functions."""

from types import MappingProxyType
from typing import Any, NotRequired, Required

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
from custom_components.haeo.elements import battery
from custom_components.haeo.elements import node as node_schema
from custom_components.haeo import elements as elements_module


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
            "common": {"name": "test"},
        },  # Missing required battery fields
        {
            "element_type": "connection",
            "common": {"name": "test"},
            "endpoints": {"source": "a"},
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
            "common": {"name": 123},
            "advanced": {"is_source": False, "is_sink": False},
        },
        # Wrong type for connection (should be str)
        {
            "element_type": "grid",
            "common": {"name": "test", "connection": ["list_not_str"]},
            "pricing": {
                "price_source_target": ["sensor.import"],
                "price_target_source": ["sensor.export"],
            },
            "power_limits": {},
        },
        # Wrong type for capacity (bool is rejected - bools are explicitly excluded from
        # constant value handling even though bool is a subclass of int in Python)
        {
            "element_type": "battery",
            "common": {
                "name": "test",
                "connection": "bus",
            },
            "storage": {
                "capacity": True,
                "initial_charge_percentage": ["sensor.soc"],
            },
            "limits": {},
            "power_limits": {},
            "pricing": {},
            "advanced": {},
            "undercharge": {},
            "overcharge": {},
        },
    ],
)
def test_is_element_config_schema_wrong_field_types(input_data: dict[str, Any]) -> None:
    """Test is_element_config_schema rejects fields with wrong types for required fields."""
    assert is_element_config_schema(input_data) is False


def test_is_element_config_schema_valid_node() -> None:
    """Test is_element_config_schema with valid node config."""
    valid_config = {
        "element_type": "node",
        "common": {"name": "test_node"},
        "advanced": {"is_source": False, "is_sink": False},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_node_minimal() -> None:
    """Test is_element_config_schema with minimal node config (optional fields omitted)."""
    valid_config = {
        "element_type": "node",
        "common": {"name": "test_node"},
        "advanced": {},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_battery() -> None:
    """Test is_element_config_schema with valid battery config."""
    valid_config = {
        "element_type": "battery",
        "common": {
            "name": "test_battery",
            "connection": "main_bus",
        },
        "storage": {
            "capacity": "sensor.capacity",
            "initial_charge_percentage": "sensor.soc",
        },
        "limits": {
            "min_charge_percentage": 10.0,
            "max_charge_percentage": 90.0,
        },
        "power_limits": {
            "max_power_source_target": 5.0,
            "max_power_target_source": 5.0,
        },
        "pricing": {
            "price_target_source": 0.05,
        },
        "advanced": {},
        "undercharge": {},
        "overcharge": {},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_grid() -> None:
    """Test is_element_config_schema with valid grid config."""
    valid_config = {
        "element_type": "grid",
        "common": {"name": "test_grid", "connection": "main_bus"},
        "pricing": {
            "price_source_target": ["sensor.import"],  # list for chaining
            "price_target_source": ["sensor.export"],  # list for chaining
        },
        "power_limits": {},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_grid_minimal() -> None:
    """Test is_element_config_schema with minimal valid grid config (prices required)."""
    valid_config = {
        "element_type": "grid",
        "common": {"name": "test_grid", "connection": "main_bus"},
        "pricing": {
            "price_source_target": 0.25,
            "price_target_source": 0.05,
        },
        "power_limits": {},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_connection() -> None:
    """Test is_element_config_schema with valid connection config."""
    valid_config = {
        "element_type": "connection",
        "common": {
            "name": "test_connection",
        },
        "endpoints": {
            "source": "battery",
            "target": "grid",
        },
        "power_limits": {},
        "pricing": {},
        "advanced": {},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_load() -> None:
    """Test is_element_config_schema with valid load config."""
    valid_config = {
        "element_type": "load",
        "common": {"name": "test_load", "connection": "main_bus"},
        "forecast": {"forecast": ["sensor.load_forecast"]},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_solar() -> None:
    """Test is_element_config_schema with valid solar config."""
    valid_config = {
        "element_type": "solar",
        "common": {"name": "test_solar", "connection": "main_bus"},
        "forecast": {"forecast": ["sensor.solar_forecast"]},
        "pricing": {"price_source_target": 0.0},
        "advanced": {"curtailment": True},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_inverter() -> None:
    """Test is_element_config_schema with valid inverter config."""
    valid_config = {
        "element_type": "inverter",
        "common": {"name": "test_inverter", "connection": "ac_bus"},
        "power_limits": {
            "max_power_source_target": "sensor.dc_to_ac",
            "max_power_target_source": "sensor.ac_to_dc",
        },
        "advanced": {},
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_battery_section() -> None:
    """Test is_element_config_schema with valid battery_section config."""
    valid_config = {
        "element_type": "battery_section",
        "common": {"name": "test_section"},
        "storage": {"capacity": "sensor.capacity", "initial_charge": "sensor.charge"},
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
        "common": {"name": "test_battery"},
        # Missing required keys like connection/capacity/initial_charge_percentage.
    }
    assert is_element_config_data(invalid_config) is False


def test_is_element_config_data_valid_node() -> None:
    """Test is_element_config_data with minimal valid node config."""
    valid_config = {
        "element_type": "node",
        "common": {"name": "test_node"},
        "advanced": {},
    }
    assert is_element_config_data(valid_config) is True


def test_is_element_config_data_optional_type_validation() -> None:
    """Test is_element_config_data validates optional key types."""
    invalid_config = {
        "element_type": node_schema.ELEMENT_TYPE,
        "common": {"name": "test_node"},
        "advanced": {"is_source": "yes"},
    }
    assert is_element_config_data(invalid_config) is False

    valid_config = {
        "element_type": node_schema.ELEMENT_TYPE,
        "common": {"name": "test_node"},
        "advanced": {"is_source": True},
    }
    assert is_element_config_data(valid_config) is True


def test_unwrap_required_type_handles_required_wrappers() -> None:
    """Test _unwrap_required_type returns underlying Required types."""
    assert elements_module._unwrap_required_type(NotRequired[bool]) is bool
    assert elements_module._unwrap_required_type(Required[int]) is int


def test_conforms_to_typed_dict_skips_optional_without_hint() -> None:
    """Test optional keys without hints are ignored when validating."""

    class _Dummy:
        __required_keys__ = frozenset()
        __optional_keys__ = frozenset({"optional"})

    assert elements_module._conforms_to_typed_dict(
        {"optional": 1},
        _Dummy,
        check_optional=True,
    )


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
