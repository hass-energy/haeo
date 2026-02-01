"""Grid element schema definitions."""

from typing import Any, Final, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.sections import (
    SECTION_BASIC,
    SECTION_LIMITS,
    SECTION_PRICING,
    BasicNameConnectionConfig,
    BasicNameConnectionData,
)

ELEMENT_TYPE: Final = "grid"

CONF_IMPORT_PRICE: Final = "import_price"
CONF_EXPORT_PRICE: Final = "export_price"
CONF_IMPORT_LIMIT: Final = "import_limit"
CONF_EXPORT_LIMIT: Final = "export_limit"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_IMPORT_LIMIT, CONF_EXPORT_LIMIT})


class GridPricingConfig(TypedDict):
    """Pricing configuration for grid elements."""

    import_price: list[str] | str | float
    export_price: list[str] | str | float


class GridPricingData(TypedDict):
    """Loaded pricing values for grid elements."""

    import_price: NDArray[np.floating[Any]] | float
    export_price: NDArray[np.floating[Any]] | float


class GridLimitsConfig(TypedDict, total=False):
    """Optional import/export power limits configuration."""

    import_limit: str | float
    export_limit: str | float


class GridLimitsData(TypedDict, total=False):
    """Loaded import/export power limits."""

    import_limit: NDArray[np.floating[Any]] | float
    export_limit: NDArray[np.floating[Any]] | float


class GridConfigSchema(TypedDict):
    """Grid element configuration as stored in Home Assistant."""

    element_type: Literal["grid"]
    basic: BasicNameConnectionConfig
    pricing: GridPricingConfig
    limits: GridLimitsConfig


class GridConfigData(TypedDict):
    """Grid element configuration with loaded values."""

    element_type: Literal["grid"]
    basic: BasicNameConnectionData
    pricing: GridPricingData
    limits: GridLimitsData


__all__ = [
    "CONF_EXPORT_LIMIT",
    "CONF_EXPORT_PRICE",
    "CONF_IMPORT_LIMIT",
    "CONF_IMPORT_PRICE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_BASIC",
    "SECTION_LIMITS",
    "SECTION_PRICING",
    "GridConfigData",
    "GridConfigSchema",
]
