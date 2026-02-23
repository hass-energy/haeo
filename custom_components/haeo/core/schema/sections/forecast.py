"""Section types for forecast configuration."""

from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.schema import ConstantValue, EntityValue

SECTION_FORECAST: Final = "forecast"
CONF_FORECAST: Final = "forecast"


class ForecastConfig(TypedDict):
    """Forecast configuration for input values."""

    forecast: EntityValue | ConstantValue


class ForecastData(TypedDict):
    """Loaded forecast values for inputs."""

    forecast: NDArray[np.floating[Any]] | float
