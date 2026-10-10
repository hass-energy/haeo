"""Tests for translation placeholders built from element configuration."""

from types import MappingProxyType

from homeassistant.config_entries import ConfigSubentry

from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.entities.translation_placeholders import build_translation_placeholders


def _subentry(data: dict[str, object], title: str = "Element") -> ConfigSubentry:
    return ConfigSubentry(data=MappingProxyType(data), subentry_type="connection", title=title, unique_id=None)


def test_schema_values_render_as_text() -> None:
    """Schema values render as the text a user would recognize."""
    placeholders = build_translation_placeholders(
        _subentry(
            {
                "entity": as_entity_value(["sensor.a", "sensor.b"]),
                "constant": as_constant_value(2.5),
                "none": as_none_value(),
                "target": as_connection_target("Switchboard"),
                "plain": 3,
            }
        )
    )

    assert placeholders == {
        "entity": "sensor.a, sensor.b",
        "constant": "2.5",
        "none": "",
        "target": "Switchboard",
        "plain": "3",
        "name": "Element",
    }


def test_section_fields_are_flattened() -> None:
    """Fields inside sections, such as a connection's endpoints, are available by name."""
    placeholders = build_translation_placeholders(
        _subentry(
            {
                "name": "ACEV to EV1",
                "endpoints": {"source": as_connection_target("ACEV Charger"), "target": as_connection_target("EV1")},
            }
        )
    )

    assert placeholders == {"name": "ACEV to EV1", "source": "ACEV Charger", "target": "EV1"}


def test_top_level_field_takes_precedence_over_section_field() -> None:
    """A section field never replaces a top-level field of the same name, whatever the order."""
    placeholders = build_translation_placeholders(
        _subentry({"limits": {"capacity": as_constant_value(1.0)}, "capacity": as_constant_value(9.0)})
    )

    assert placeholders["capacity"] == "9.0"
