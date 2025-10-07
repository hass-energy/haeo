"""Constant load element configuration for HAEO integration."""

from dataclasses import dataclass
from typing import Literal

from custom_components.haeo.schema.fields import NameField, PowerField


@dataclass
class ConstantLoadConfig:
    """Constant load element configuration."""

    name: NameField

    power: PowerField

    element_type: Literal["constant_load"] = "constant_load"
