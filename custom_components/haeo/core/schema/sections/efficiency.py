"""Section types for efficiency configuration."""

from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.schema import ConstantValue, EntityValue, NoneValue

SECTION_EFFICIENCY: Final = "efficiency"

CONF_EFFICIENCY_SOURCE_TARGET: Final = "efficiency_source_target"
CONF_EFFICIENCY_TARGET_SOURCE: Final = "efficiency_target_source"

type EfficiencyValueConfig = EntityValue | ConstantValue | NoneValue
type EfficiencyValueData = NDArray[np.floating[Any]] | float


class EfficiencyConfig(TypedDict, total=False):
    """Efficiency configuration across element types."""

    efficiency_source_target: EfficiencyValueConfig
    efficiency_target_source: EfficiencyValueConfig


class EfficiencyData(TypedDict, total=False):
    """Loaded efficiency values across element types."""

    efficiency_source_target: EfficiencyValueData
    efficiency_target_source: EfficiencyValueData
