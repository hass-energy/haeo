"""Section types for power limit configuration."""

from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.schema import ConstantValue, EntityValue, NoneValue

SECTION_POWER_LIMITS: Final = "power_limits"
CONF_MAX_POWER_SOURCE_TARGET: Final = "max_power_source_target"
CONF_MAX_POWER_TARGET_SOURCE: Final = "max_power_target_source"


class PowerLimitsConfig(TypedDict, total=False):
    """Directional power limit configuration."""

    max_power_source_target: EntityValue | ConstantValue | NoneValue
    max_power_target_source: EntityValue | ConstantValue | NoneValue


class PowerLimitsData(TypedDict, total=False):
    """Loaded directional power limits."""

    max_power_source_target: NDArray[np.floating[Any]] | float
    max_power_target_source: NDArray[np.floating[Any]] | float
