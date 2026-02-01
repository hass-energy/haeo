"""Shared section definitions for HAEO element configuration."""

# ruff: noqa: I001

from .advanced import advanced_section, SECTION_ADVANCED
from .basic import (
    basic_section,
    BasicNameConfig,
    BasicNameConnectionConfig,
    BasicNameConnectionData,
    BasicNameData,
    build_connection_field,
    build_name_field,
    CONF_CONNECTION,
    SECTION_BASIC,
)
from .inputs import (
    CONF_FORECAST,
    ForecastInputsConfig,
    ForecastInputsData,
    inputs_section,
    SECTION_INPUTS,
)
from .limits import limits_section, SECTION_LIMITS
from .pricing import pricing_section, SECTION_PRICING
from .storage import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    SECTION_STORAGE,
    storage_section,
)

__all__ = [
    "CONF_CAPACITY",
    "CONF_CONNECTION",
    "CONF_FORECAST",
    "CONF_INITIAL_CHARGE",
    "CONF_INITIAL_CHARGE_PERCENTAGE",
    "SECTION_ADVANCED",
    "SECTION_BASIC",
    "SECTION_INPUTS",
    "SECTION_LIMITS",
    "SECTION_PRICING",
    "SECTION_STORAGE",
    "BasicNameConfig",
    "BasicNameConnectionConfig",
    "BasicNameConnectionData",
    "BasicNameData",
    "ForecastInputsConfig",
    "ForecastInputsData",
    "advanced_section",
    "basic_section",
    "build_connection_field",
    "build_name_field",
    "inputs_section",
    "limits_section",
    "pricing_section",
    "storage_section",
]
