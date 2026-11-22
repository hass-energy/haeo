"""Fixtures for config flow tests."""

# Tests drive element-specific flow classes dynamically (per-element step methods,
# monkeypatched async_create_entry), which a static flow base type cannot express.
from typing import Any  # noqa: TID251

from homeassistant.config_entries import SubentryFlowResult
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.flows import get_element_flow_classes


def create_flow(hass: HomeAssistant, hub_entry: MockConfigEntry, element_type: ElementType) -> Any:
    """Create a configured subentry flow instance for an element type."""
    flow_classes = get_element_flow_classes()
    flow_class = flow_classes[element_type]
    flow = flow_class()
    flow.hass = hass
    flow.handler = (hub_entry.entry_id, element_type)
    return flow


def section_suggested_values(form: SubentryFlowResult, section_key: str) -> dict[str, object]:
    """Return the value each field of a shown form's section opens with, keyed by field name."""
    data_schema = form.get("data_schema")
    assert data_schema is not None
    section_schema = data_schema.schema[section_key].schema
    return {str(marker): (marker.description or {}).get("suggested_value") for marker in section_schema.schema}


def section_selectors(form: SubentryFlowResult, section_key: str) -> dict[str, Any]:
    """Return the selector of each field of a shown form's section, keyed by field name."""
    data_schema = form.get("data_schema")
    assert data_schema is not None
    section_schema = data_schema.schema[section_key].schema
    return {str(marker): selector for marker, selector in section_schema.schema.items()}
