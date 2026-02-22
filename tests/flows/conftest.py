"""Fixtures for config flow tests."""

from typing import Any

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.elements import ElementType
from custom_components.haeo.flows import get_element_flow_classes


def create_flow(hass: HomeAssistant, hub_entry: MockConfigEntry, element_type: ElementType) -> Any:
    """Create a configured subentry flow instance for an element type."""
    flow_classes = get_element_flow_classes()
    flow_class = flow_classes[element_type]
    flow = flow_class()
    flow.hass = hass
    flow.handler = (hub_entry.entry_id, element_type)
    return flow
