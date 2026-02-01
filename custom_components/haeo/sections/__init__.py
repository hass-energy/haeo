"""Shared section definitions for HAEO element configuration."""

# ruff: noqa: I001

from .advanced import AdvancedConfig, AdvancedData, SECTION_ADVANCED, advanced_section, build_advanced_fields
from .details import (
    CONF_CONNECTION,
    DetailsConfig,
    DetailsData,
    SECTION_DETAILS,
    build_details_fields,
    details_section,
)
from .forecast import (
    CONF_FORECAST,
    ForecastConfig,
    ForecastData,
    SECTION_FORECAST,
    build_forecast_fields,
    forecast_section,
)
from .limits import LimitsConfig, LimitsData, SECTION_LIMITS, build_limits_fields, limits_section
from .pricing import PricingConfig, PricingData, SECTION_PRICING, build_pricing_fields, pricing_section
from .storage import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    SECTION_STORAGE,
    StorageConfig,
    StorageData,
    build_storage_fields,
    storage_section,
)

__all__ = [
    "AdvancedConfig",
    "AdvancedData",
    "CONF_CAPACITY",
    "CONF_CONNECTION",
    "CONF_FORECAST",
    "CONF_INITIAL_CHARGE",
    "CONF_INITIAL_CHARGE_PERCENTAGE",
    "DetailsConfig",
    "DetailsData",
    "ForecastConfig",
    "ForecastData",
    "LimitsConfig",
    "LimitsData",
    "PricingConfig",
    "PricingData",
    "SECTION_ADVANCED",
    "SECTION_DETAILS",
    "SECTION_FORECAST",
    "SECTION_LIMITS",
    "SECTION_PRICING",
    "SECTION_STORAGE",
    "StorageConfig",
    "StorageData",
    "advanced_section",
    "build_advanced_fields",
    "build_details_fields",
    "build_forecast_fields",
    "build_limits_fields",
    "build_pricing_fields",
    "build_storage_fields",
    "details_section",
    "forecast_section",
    "limits_section",
    "pricing_section",
    "storage_section",
]
