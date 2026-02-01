"""Grid element schema definitions."""

from typing import Final, Literal, TypedDict

from custom_components.haeo.sections import (
    SECTION_DETAILS,
    SECTION_LIMITS,
    SECTION_PRICING,
    DetailsConfig,
    DetailsData,
    LimitsConfig,
    LimitsData,
    PricingConfig,
    PricingData,
)

ELEMENT_TYPE: Final = "grid"

CONF_IMPORT_PRICE: Final = "import_price"
CONF_EXPORT_PRICE: Final = "export_price"
CONF_IMPORT_LIMIT: Final = "import_limit"
CONF_EXPORT_LIMIT: Final = "export_limit"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_IMPORT_LIMIT, CONF_EXPORT_LIMIT})


class GridConfigSchema(TypedDict):
    """Grid element configuration as stored in Home Assistant."""

    element_type: Literal["grid"]
    basic: DetailsConfig
    pricing: PricingConfig
    limits: LimitsConfig


class GridConfigData(TypedDict):
    """Grid element configuration with loaded values."""

    element_type: Literal["grid"]
    basic: DetailsData
    pricing: PricingData
    limits: LimitsData


__all__ = [
    "CONF_EXPORT_LIMIT",
    "CONF_EXPORT_PRICE",
    "CONF_IMPORT_LIMIT",
    "CONF_IMPORT_PRICE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_DETAILS",
    "SECTION_LIMITS",
    "SECTION_PRICING",
    "GridConfigData",
    "GridConfigSchema",
]
