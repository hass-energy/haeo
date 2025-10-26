"""Additional edge case tests to improve coverage."""

from custom_components.haeo.elements import is_element_config_schema
from custom_components.haeo.elements.battery import model_description as battery_description
from custom_components.haeo.elements.grid import model_description as grid_description


def test_battery_description_with_none_initial_charge() -> None:
    """Test battery description when initial_charge_percentage is None (line 83)."""
    config = {
        "element_type": "battery",
        "name": "Test Battery",
        "capacity": 10000,
        "initial_charge_percentage": None,
    }
    # Should handle None gracefully
    description = battery_description(config)  # type: ignore[arg-type]
    assert "Battery" in description
    assert "10000.0kWh" in description or "10.0kWh" in description


def test_grid_description_with_export_only() -> None:
    """Test grid description when only export_limit is set (line 66)."""
    config = {"element_type": "grid", "name": "Test Grid", "export_limit": 5.0}
    description = grid_description(config)  # type: ignore[arg-type]
    assert "Export 5.0kW" in description


def test_is_element_config_schema_not_mapping() -> None:
    """Test is_element_config_schema with non-Mapping input (line 143)."""
    # Test with a list (not a Mapping)
    assert is_element_config_schema([1, 2, 3]) is False

    # Test with a string
    assert is_element_config_schema("not a config") is False

    # Test with None
    assert is_element_config_schema(None) is False
