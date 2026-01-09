"""Network element schema definitions."""

from typing import Literal, TypedDict

ElementTypeName = Literal["network"]
ELEMENT_TYPE: ElementTypeName = "network"


class NetworkConfigSchema(TypedDict):
    """Network element configuration as stored in Home Assistant.

    The network element represents the overall optimization network.
    It is auto-created and has no user-configurable fields.
    """

    element_type: Literal["network"]
    name: str


class NetworkConfigData(TypedDict):
    """Network element loaded configuration data.

    Contains the same fields as NetworkConfigSchema since
    the network element has no sensor-loaded values.
    """

    element_type: Literal["network"]
    name: str
