"""Section types for curtailment configuration."""

from typing import Final, TypedDict

from custom_components.haeo.schema import ConstantValue, EntityValue

SECTION_CURTAILMENT: Final = "curtailment"

CONF_CURTAILMENT: Final = "curtailment"


class CurtailmentConfig(TypedDict, total=False):
    """Curtailment configuration values."""

    curtailment: EntityValue | ConstantValue


class CurtailmentData(TypedDict, total=False):
    """Loaded curtailment values."""

    curtailment: bool
