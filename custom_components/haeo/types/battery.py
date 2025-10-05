"""Battery element configuration for HAEO integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from custom_components.haeo.schema.fields import (
    BatterySOCField,
    BatterySOCSensorField,
    EnergyField,
    NameField,
    PercentageField,
    PowerField,
    PriceField,
)


@dataclass
class BatteryConfig:
    """Battery element configuration."""

    name: NameField

    capacity: EnergyField
    initial_charge_percentage: BatterySOCSensorField

    min_charge_percentage: BatterySOCField = 10
    max_charge_percentage: BatterySOCField = 90
    efficiency: PercentageField = 99

    max_charge_power: PowerField | None = None
    max_discharge_power: PowerField | None = None
    charge_cost: PriceField | None = None
    discharge_cost: PriceField | None = None

    element_type: Literal["battery"] = "battery"
