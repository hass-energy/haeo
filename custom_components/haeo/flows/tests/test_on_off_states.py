"""Tests for the step asking which states mean on and off."""

import json
from pathlib import Path

from homeassistant.core import HomeAssistant
import pytest

from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import as_entity_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.elements import get_input_fields
from custom_components.haeo.elements.input_fields import reads_calendar
from custom_components.haeo.flows.on_off_states import STEP_STATES, fields_reading_words

TRANSLATIONS = Path(__file__).parents[2] / "translations" / "en.json"


def _has_on_off_entity_field(element_type: ElementType) -> bool:
    """Return True when an element type has an on/off field that reads entities."""
    return any(
        info.output_type is OutputType.AVAILABILITY and not reads_calendar(info)
        for fields in get_input_fields(element_type).values()
        for info in fields.values()
    )


@pytest.mark.parametrize("element_type", [t for t in ELEMENT_TYPES if _has_on_off_entity_field(t)])
def test_element_types_with_on_off_fields_translate_the_states_step(element_type: str) -> None:
    """Every element type with an on/off field reading entities has the states step translated."""
    subentry = json.loads(TRANSLATIONS.read_text())["config_subentries"][element_type]

    assert {"title", "description", "data"} <= set(subentry["step"][STEP_STATES])
    assert "states_required" in subentry["error"]


async def test_states_are_asked_only_for_on_off_fields_reading_words(hass: HomeAssistant) -> None:
    """Only on/off fields whose entities report words need states, and fields that already have them are asked again."""
    hass.states.async_set("sensor.charger", "Charging")
    hass.states.async_set("sensor.flag", "0")
    input_fields = get_input_fields(ElementType.EV)
    config = {
        "charging": {"connected": as_entity_value(["sensor.charger"], off_states=["Idle"])},
        "vehicle": {"current_soc": as_entity_value(["sensor.soc"])},
    }

    assert fields_reading_words(hass, config, input_fields) == [("charging", "connected")]

    config["charging"]["connected"] = as_entity_value(["sensor.flag"])
    assert fields_reading_words(hass, config, input_fields) == []
