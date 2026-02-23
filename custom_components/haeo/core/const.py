"""Constants for the HAEO core module."""

import enum
from typing import Final

CONF_ELEMENT_TYPE: Final = "element_type"
CONF_NAME: Final = "name"


class ConnectivityLevel(enum.StrEnum):
    """Connectivity level for element types in connection selectors.

    - ALWAYS: Always shown in connection selectors
    - ADVANCED: Only shown when advanced mode is enabled
    - NEVER: Never shown in connection selectors
    """

    ALWAYS = enum.auto()
    ADVANCED = enum.auto()
    NEVER = enum.auto()
