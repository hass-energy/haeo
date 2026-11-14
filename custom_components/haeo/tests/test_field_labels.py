"""Tests for naming an input field by its form label."""

from types import MappingProxyType

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_constant_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.ev import (
    CONF_ENERGY_PER_DISTANCE,
    CONF_TRIP_DUE,
    SECTION_TRIP,
    SECTION_VEHICLE,
)
from custom_components.haeo.core.schema.elements.policy import CONF_ENABLED, CONF_PRICE, CONF_RULE_NAME, CONF_RULES
from custom_components.haeo.elements import InputFieldPath
from custom_components.haeo.field_labels import input_field_label


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a hub entry with an EV and a policy holding two rules."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="hub")
    entry.add_to_hass(hass)
    for element_type, name, data in (
        (ElementType.EV, "Atto 2", {}),
        (
            ElementType.POLICY,
            "Policies",
            {
                CONF_RULES: [
                    {CONF_RULE_NAME: "Solar export", CONF_ENABLED: True, CONF_PRICE: as_constant_value(0.02)},
                    {CONF_RULE_NAME: "Battery export", CONF_ENABLED: True, CONF_PRICE: as_constant_value(0.05)},
                ]
            },
        ),
    ):
        hass.config_entries.async_add_subentry(
            entry,
            ConfigSubentry(
                data=MappingProxyType({CONF_ELEMENT_TYPE: element_type, CONF_NAME: name, **data}),
                subentry_type=element_type,
                title=name,
                unique_id=None,
            ),
        )
    return entry


@pytest.mark.usefixtures("haeo_translations")
@pytest.mark.parametrize(
    ("element_name", "field_path", "expected"),
    [
        pytest.param("Atto 2", (SECTION_VEHICLE, CONF_ENERGY_PER_DISTANCE), "Energy per distance", id="section_field"),
        pytest.param("Atto 2", (SECTION_TRIP, CONF_TRIP_DUE), "Trip calendar", id="field_fed_by_another"),
        pytest.param("Policies", (CONF_RULES, "1", CONF_PRICE), "Price (Battery export)", id="list_item_field"),
    ],
)
def test_input_field_label_names_the_form_field(
    hass: HomeAssistant, entry: MockConfigEntry, element_name: str, field_path: InputFieldPath, expected: str
) -> None:
    """An input is named by the label its element's form shows for the field it reads."""
    assert input_field_label(hass, entry.entry_id, element_name, field_path) == expected


def test_input_field_label_falls_back_to_the_path_without_translations(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The field's path names it in a language whose translations are not loaded."""
    hass.config.language = "xx"

    assert (
        input_field_label(hass, entry.entry_id, "Atto 2", (SECTION_VEHICLE, CONF_ENERGY_PER_DISTANCE))
        == "vehicle.energy_per_distance"
    )
