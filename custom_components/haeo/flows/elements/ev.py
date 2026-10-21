"""EV element configuration flows."""

from typing import ClassVar

from custom_components.haeo.core.schema.elements.ev import (
    CONF_CAPACITY,
    CONF_CHARGE_LIMIT_COST,
    CONF_CONNECTED,
    CONF_CURRENT_SOC,
    CONF_ENERGY_PER_DISTANCE,
    CONF_MAX_CHARGE_RATE,
    CONF_MAX_DISCHARGE_RATE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_ODOMETER,
    CONF_PUBLIC_CHARGING_PRICE,
    CONF_TRIP_CALENDAR,
    ELEMENT_TYPE,
    SECTION_ADVANCED,
    SECTION_CHARGING,
    SECTION_PUBLIC_CHARGING,
    SECTION_TRIP,
    SECTION_VEHICLE,
)
from custom_components.haeo.core.schema.sections import CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE
from custom_components.haeo.flows.connected_flow import ConnectedElementSubentryFlow
from custom_components.haeo.flows.field_schema import SectionDefinition
from custom_components.haeo.sections import efficiency_section


class EvSubentryFlowHandler(ConnectedElementSubentryFlow):
    """Handle EV element configuration flows."""

    element_type = ELEMENT_TYPE

    sections: ClassVar[tuple[SectionDefinition, ...]] = (
        SectionDefinition(
            key=SECTION_VEHICLE,
            fields=(CONF_CAPACITY, CONF_ENERGY_PER_DISTANCE, CONF_CURRENT_SOC, CONF_MIN_CHARGE_PERCENTAGE),
            collapsed=False,
        ),
        SectionDefinition(
            key=SECTION_CHARGING,
            fields=(CONF_MAX_CHARGE_RATE, CONF_MAX_DISCHARGE_RATE, CONF_CONNECTED),
            collapsed=False,
        ),
        SectionDefinition(
            key=SECTION_TRIP,
            fields=(
                CONF_TRIP_CALENDAR,
                CONF_ODOMETER,
            ),
            collapsed=True,
        ),
        SectionDefinition(
            key=SECTION_PUBLIC_CHARGING,
            fields=(CONF_PUBLIC_CHARGING_PRICE,),
            collapsed=True,
        ),
        efficiency_section(
            (CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE),
            collapsed=True,
        ),
        SectionDefinition(key=SECTION_ADVANCED, fields=(CONF_CHARGE_LIMIT_COST,), collapsed=True),
    )
