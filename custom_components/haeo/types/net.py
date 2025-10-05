"""Network node element configuration for HAEO integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .fields import NameField


@dataclass
class NetConfig:
    """Net element configuration."""

    name: NameField

    element_type: Literal["net"] = "net"
