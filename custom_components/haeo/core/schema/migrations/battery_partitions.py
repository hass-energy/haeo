"""Battery partition keys from before reserves and headroom replaced them.

Batteries used to price an undercharge range below their min charge and an
overcharge range above their max charge. Migrations still read these keys
from older configs.
"""

from typing import Final

SECTION_PARTITIONING: Final = "partitioning"
SECTION_UNDERCHARGE: Final = "undercharge"
SECTION_OVERCHARGE: Final = "overcharge"

CONF_CONFIGURE_PARTITIONS: Final = "configure_partitions"
CONF_PARTITION_PERCENTAGE: Final = "percentage"
CONF_PARTITION_COST: Final = "cost"

__all__ = [
    "CONF_CONFIGURE_PARTITIONS",
    "CONF_PARTITION_COST",
    "CONF_PARTITION_PERCENTAGE",
    "SECTION_OVERCHARGE",
    "SECTION_PARTITIONING",
    "SECTION_UNDERCHARGE",
]
