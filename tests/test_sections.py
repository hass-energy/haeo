"""Tests for shared section helpers."""

from __future__ import annotations

from homeassistant.components.number import NumberEntityDescription
from homeassistant.core import HomeAssistant
import voluptuous as vol

from custom_components.haeo.elements.field_schema import FieldSchemaInfo
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.schema import ConstantValue, EntityValue
from custom_components.haeo.sections import (
    CONF_CURTAILMENT,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_FORECAST,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_PRICE_SOURCE_TARGET,
    SECTION_CURTAILMENT,
    SECTION_EFFICIENCY,
    SECTION_FORECAST,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    build_curtailment_fields,
    build_efficiency_fields,
    build_forecast_fields,
    build_power_limits_fields,
    build_pricing_fields,
    curtailment_section,
    efficiency_section,
    forecast_section,
    power_limits_section,
    pricing_section,
)


def _number_field(name: str) -> InputFieldInfo[NumberEntityDescription]:
    """Create a simple InputFieldInfo for a number field."""
    return InputFieldInfo(
        field_name=name,
        entity_description=NumberEntityDescription(key=name, translation_key=name),
        output_type=OutputType.POWER,
    )


def _field_schema(field_info: InputFieldInfo[NumberEntityDescription]) -> dict[str, FieldSchemaInfo]:
    """Create minimal schema info for a field."""
    return {field_info.field_name: FieldSchemaInfo(value_type=EntityValue | ConstantValue, is_optional=False)}


def test_efficiency_section_helpers(hass: HomeAssistant) -> None:
    """Efficiency section helpers should return definitions and entries."""
    section = efficiency_section((CONF_EFFICIENCY_SOURCE_TARGET,), collapsed=False)
    assert section.key == SECTION_EFFICIENCY
    assert section.fields == (CONF_EFFICIENCY_SOURCE_TARGET,)
    assert section.collapsed is False

    assert build_efficiency_fields({}, field_schema={}, inclusion_map={}) == {}

    field_info = _number_field(CONF_EFFICIENCY_SOURCE_TARGET)
    entries = build_efficiency_fields(
        {field_info.field_name: field_info},
        field_schema=_field_schema(field_info),
        inclusion_map={},
        current_data={},
    )
    marker, _selector = entries[field_info.field_name]
    assert isinstance(marker, vol.Marker)


def test_forecast_section_helpers(hass: HomeAssistant) -> None:
    """Forecast section helpers should return definitions and entries."""
    section = forecast_section((CONF_FORECAST,), collapsed=True)
    assert section.key == SECTION_FORECAST
    assert section.fields == (CONF_FORECAST,)
    assert section.collapsed is True

    assert build_forecast_fields({}, field_schema={}, inclusion_map={}) == {}

    field_info = _number_field(CONF_FORECAST)
    entries = build_forecast_fields(
        {field_info.field_name: field_info},
        field_schema=_field_schema(field_info),
        inclusion_map={},
        current_data={},
    )
    marker, _selector = entries[field_info.field_name]
    assert isinstance(marker, vol.Marker)


def test_power_limits_section_helpers(hass: HomeAssistant) -> None:
    """Power limits section helpers should return definitions and entries."""
    section = power_limits_section((CONF_MAX_POWER_SOURCE_TARGET,), key=SECTION_POWER_LIMITS, collapsed=True)
    assert section.key == SECTION_POWER_LIMITS
    assert section.fields == (CONF_MAX_POWER_SOURCE_TARGET,)
    assert section.collapsed is True

    assert build_power_limits_fields({}, field_schema={}, inclusion_map={}) == {}

    field_info = _number_field(CONF_MAX_POWER_SOURCE_TARGET)
    entries = build_power_limits_fields(
        {field_info.field_name: field_info},
        field_schema=_field_schema(field_info),
        inclusion_map={},
        current_data={},
    )
    marker, _selector = entries[field_info.field_name]
    assert isinstance(marker, vol.Marker)


def test_pricing_section_helpers(hass: HomeAssistant) -> None:
    """Pricing section helpers should return definitions and entries."""
    section = pricing_section((CONF_PRICE_SOURCE_TARGET,), collapsed=True)
    assert section.key == SECTION_PRICING
    assert section.fields == (CONF_PRICE_SOURCE_TARGET,)
    assert section.collapsed is True

    assert build_pricing_fields({}, field_schema={}, inclusion_map={}) == {}

    field_info = _number_field(CONF_PRICE_SOURCE_TARGET)
    entries = build_pricing_fields(
        {field_info.field_name: field_info},
        field_schema=_field_schema(field_info),
        inclusion_map={},
        current_data={},
    )
    marker, _selector = entries[field_info.field_name]
    assert isinstance(marker, vol.Marker)


def test_curtailment_section_helpers(hass: HomeAssistant) -> None:
    """Curtailment section helpers should return definitions and entries."""
    section = curtailment_section((CONF_CURTAILMENT,), collapsed=True)
    assert section.key == SECTION_CURTAILMENT
    assert section.fields == (CONF_CURTAILMENT,)
    assert section.collapsed is True

    assert build_curtailment_fields({}, field_schema={}, inclusion_map={}) == {}

    field_info = _number_field(CONF_CURTAILMENT)
    entries = build_curtailment_fields(
        {field_info.field_name: field_info},
        field_schema=_field_schema(field_info),
        inclusion_map={},
        current_data={},
    )
    marker, _selector = entries[field_info.field_name]
    assert isinstance(marker, vol.Marker)
