"""Network node element configuration for HAEO integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from custom_components.haeo.schema.fields import NameField


@dataclass
class NetConfig:
    """Net element configuration."""

    name: NameField

    element_type: Literal["net"] = "net"
