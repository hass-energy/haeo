"""Section types for pricing configuration."""

from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.schema import ConstantValue, EntityValue, NoneValue

SECTION_PRICING: Final = "pricing"
CONF_PRICE_SOURCE_TARGET: Final = "price_source_target"
CONF_PRICE_TARGET_SOURCE: Final = "price_target_source"


class PricingConfig(TypedDict, total=False):
    """Directional pricing configuration for power transfer."""

    price_source_target: EntityValue | ConstantValue | NoneValue
    price_target_source: EntityValue | ConstantValue | NoneValue


class PricingData(TypedDict, total=False):
    """Loaded directional pricing values."""

    price_source_target: NDArray[np.floating[Any]] | float
    price_target_source: NDArray[np.floating[Any]] | float
