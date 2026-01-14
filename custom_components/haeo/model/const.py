"""Constants for HAEO energy modeling."""

from enum import StrEnum, auto


class OutputType(StrEnum):
    """Output type categories for sensors and input fields.

    These values categorize model outputs and input fields by physical meaning,
    enabling automatic unit specification lookup for entity filtering.

    Power types:
        POWER: Active power (kW)
        POWER_FLOW: Directional power flow between elements (kW)
        POWER_LIMIT: Maximum power constraints (kW)

    Energy types:
        ENERGY: Energy quantity (kWh)

    Percentage types:
        SOC: State of charge percentage (%)
        EFFICIENCY: Efficiency ratio percentage (%)

    Monetary types:
        PRICE: Price per energy unit ($/kWh, €/kWh, etc.)
        COST: Total cost in currency units

    Other types:
        STATUS: Boolean or categorical status
        DURATION: Time duration
        SHADOW_PRICE: Shadow prices from LP constraints
        CONTROL_LIMIT: Recommended power limit for automation control (kW)

    """

    POWER = auto()
    POWER_FLOW = auto()
    POWER_LIMIT = auto()
    ENERGY = auto()
    PRICE = auto()
    STATE_OF_CHARGE = auto()
    EFFICIENCY = auto()
    COST = auto()
    STATUS = auto()
    DURATION = auto()
    SHADOW_PRICE = auto()
    CONTROL_LIMIT = auto()
