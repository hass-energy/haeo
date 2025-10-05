"""Network and connection element configurations for HAEO integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .fields import ElementNameField, NameField, PowerFlowField


@dataclass
class ConnectionConfig:
    """Connection element configuration."""

    name: NameField

    source: ElementNameField
    target: ElementNameField

    min_power: PowerFlowField | None = None
    max_power: PowerFlowField | None = None

    element_type: Literal["connection"] = "connection"
