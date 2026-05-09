"""Section types for threshold-price configuration.

A threshold price gives an element (currently sheddable loads) a willingness-to-pay
ceiling expressed in $/kWh. The optimizer dispatches the element only when the
marginal value of energy at its connection node is at or below the threshold;
otherwise the element sheds. A threshold of 0 leaves the LP unchanged.
"""

from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.schema import ConstantValue, EntityValue

SECTION_THRESHOLD: Final = "threshold"

CONF_THRESHOLD_PRICE: Final = "threshold_price"


class ThresholdConfig(TypedDict, total=False):
    """Threshold-price configuration values."""

    threshold_price: EntityValue | ConstantValue


class ThresholdData(TypedDict, total=False):
    """Loaded threshold-price values."""

    threshold_price: NDArray[np.floating[Any]] | float
