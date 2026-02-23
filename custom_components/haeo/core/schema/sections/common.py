"""Section types for common configuration."""

from typing import Final, NotRequired, TypedDict

from custom_components.haeo.core.schema import ConnectionTarget

SECTION_COMMON: Final = "common"
CONF_CONNECTION: Final = "connection"


class CommonConfig(TypedDict):
    """Common configuration for element identity and connectivity."""

    name: str
    connection: NotRequired[ConnectionTarget]


class CommonData(TypedDict):
    """Loaded common values for element identity and connectivity."""

    name: str
    connection: NotRequired[ConnectionTarget]


class ConnectedCommonConfig(TypedDict):
    """Common configuration with a required connection target."""

    name: str
    connection: ConnectionTarget


class ConnectedCommonData(TypedDict):
    """Loaded common values with a required connection target."""

    name: str
    connection: ConnectionTarget
