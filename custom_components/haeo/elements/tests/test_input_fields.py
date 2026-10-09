"""Tests for input field localization."""

from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_PARTITION_COST,
    SECTION_OVERCHARGE,
    SECTION_STORAGE,
    SECTION_UNDERCHARGE,
)
from custom_components.haeo.core.schema.elements.battery import ELEMENT_TYPE as BATTERY_TYPE
from custom_components.haeo.core.schema.elements.solar import ELEMENT_TYPE as SOLAR_TYPE
from custom_components.haeo.elements import get_input_fields
from custom_components.haeo.elements.input_fields import localize_input_field, localize_input_fields


def test_localize_input_fields_replaces_currency_placeholder() -> None:
    """Monetary units take the currency symbol and every other field is returned unchanged."""
    fields = get_input_fields(BATTERY_TYPE)

    localized = localize_input_fields(fields, "€")

    for section in (SECTION_UNDERCHARGE, SECTION_OVERCHARGE):
        assert localized[section][CONF_PARTITION_COST].entity_description.native_unit_of_measurement == "€/kWh/h"
    assert localized[SECTION_STORAGE][CONF_CAPACITY] is fields[SECTION_STORAGE][CONF_CAPACITY]


def test_localize_input_field_leaves_switch_fields_unchanged() -> None:
    """Switch fields have no unit and pass through as the same object."""
    switch_field = next(info for section in get_input_fields(SOLAR_TYPE).values() for info in section.values() if type(info.entity_description).__name__ == "SwitchEntityDescription")

    assert localize_input_field(switch_field, "€") is switch_field
