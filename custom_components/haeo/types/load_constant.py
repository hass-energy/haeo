"""Constant load element configuration for HAEO integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .fields import NameField, PowerField


@dataclass
class ConstantLoadConfig:
    """Constant load element configuration."""

    name: NameField

    power: PowerField

    element_type: Literal["constant_load"] = "constant_load"
