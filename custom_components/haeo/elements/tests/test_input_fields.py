"""Tests for input field localization."""

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements.battery import CONF_COST, CONF_HOLDING_COSTS, CONF_THRESHOLD
from custom_components.haeo.core.schema.elements.battery import ELEMENT_TYPE as BATTERY_TYPE
from custom_components.haeo.core.schema.elements.grid import CONF_PRICE_SOURCE_TARGET, CONF_PRICE_TARGET_SOURCE, SECTION_PRICING
from custom_components.haeo.core.schema.elements.grid import ELEMENT_TYPE as GRID_TYPE
from custom_components.haeo.core.schema.elements.solar import ELEMENT_TYPE as SOLAR_TYPE
from custom_components.haeo.elements import get_input_fields, get_list_input_fields
from custom_components.haeo.elements.input_fields import (
    is_number_field_info,
    is_switch_field_info,
    localize_input_field,
    localize_input_fields,
)


def test_localize_input_fields_replaces_currency_placeholder() -> None:
    """Monetary units take the currency symbol and every other field is returned unchanged."""
    fields = get_list_input_fields({CONF_ELEMENT_TYPE: BATTERY_TYPE, CONF_HOLDING_COSTS: [{}]})

    localized = localize_input_fields(fields, "€")

    cost = localized[f"{CONF_HOLDING_COSTS}.0"][CONF_COST]
    assert is_number_field_info(cost)
    assert cost.entity_description.native_unit_of_measurement == "€/kWh/h"
    threshold = fields[f"{CONF_HOLDING_COSTS}.0"][CONF_THRESHOLD]
    assert localized[f"{CONF_HOLDING_COSTS}.0"][CONF_THRESHOLD] is threshold


def test_localize_input_field_leaves_switch_fields_unchanged() -> None:
    """Switch fields have no unit and pass through as the same object."""
    switch_field = next(info for section in get_input_fields(SOLAR_TYPE).values() for info in section.values() if is_switch_field_info(info))

    assert localize_input_field(switch_field, "€") is switch_field


def test_localize_input_fields_shows_prices_per_kwh() -> None:
    """Price inputs show a per-kWh unit in the currency symbol."""
    localized = localize_input_fields(get_input_fields(GRID_TYPE), "£")

    for field_name in (CONF_PRICE_SOURCE_TARGET, CONF_PRICE_TARGET_SOURCE):
        price = localized[SECTION_PRICING][field_name]
        assert is_number_field_info(price)
        assert price.entity_description.native_unit_of_measurement == "£/kWh"
