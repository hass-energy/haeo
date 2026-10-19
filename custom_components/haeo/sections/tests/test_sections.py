"""Tests for shared section helpers."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.haeo.core.schema.sections import (
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
)
from custom_components.haeo.sections import (
    curtailment_section,
    efficiency_section,
    forecast_section,
    power_limits_section,
    pricing_section,
)


def test_efficiency_section_helpers(hass: HomeAssistant) -> None:
    """Efficiency section helpers should return definitions and entries."""
    section = efficiency_section((CONF_EFFICIENCY_SOURCE_TARGET,), collapsed=False)
    assert section.key == SECTION_EFFICIENCY
    assert section.fields == (CONF_EFFICIENCY_SOURCE_TARGET,)
    assert section.collapsed is False


def test_forecast_section_helpers(hass: HomeAssistant) -> None:
    """Forecast section helpers should return definitions and entries."""
    section = forecast_section((CONF_FORECAST,), collapsed=True)
    assert section.key == SECTION_FORECAST
    assert section.fields == (CONF_FORECAST,)
    assert section.collapsed is True


def test_power_limits_section_helpers(hass: HomeAssistant) -> None:
    """Power limits section helpers should return definitions and entries."""
    section = power_limits_section((CONF_MAX_POWER_SOURCE_TARGET,), key=SECTION_POWER_LIMITS, collapsed=True)
    assert section.key == SECTION_POWER_LIMITS
    assert section.fields == (CONF_MAX_POWER_SOURCE_TARGET,)
    assert section.collapsed is True


def test_pricing_section_helpers(hass: HomeAssistant) -> None:
    """Pricing section helpers should return definitions and entries."""
    section = pricing_section((CONF_PRICE_SOURCE_TARGET,), collapsed=True)
    assert section.key == SECTION_PRICING
    assert section.fields == (CONF_PRICE_SOURCE_TARGET,)
    assert section.collapsed is True


def test_curtailment_section_helpers(hass: HomeAssistant) -> None:
    """Curtailment section helpers should return definitions and entries."""
    section = curtailment_section((CONF_CURTAILMENT,), collapsed=True)
    assert section.key == SECTION_CURTAILMENT
    assert section.fields == (CONF_CURTAILMENT,)
    assert section.collapsed is True
