"""Deferrable load element configuration flows."""

from typing import ClassVar

from custom_components.haeo.core.schema.elements.deferrable_load import (
    CONF_DEFICIT_PRICE,
    CONF_ENERGY_METER,
    CONF_MAX_POWER,
    CONF_OVERAGE_PRICE,
    CONF_WINDOW_CALENDAR,
    ELEMENT_TYPE,
    SECTION_POWER,
    SECTION_PRICING,
    SECTION_SCHEDULE,
)
from custom_components.haeo.flows.connected_flow import ConnectedElementSubentryFlow
from custom_components.haeo.flows.field_schema import SectionDefinition


class DeferrableLoadSubentryFlowHandler(ConnectedElementSubentryFlow):
    """Handle deferrable load element configuration flows."""

    element_type = ELEMENT_TYPE

    sections: ClassVar[tuple[SectionDefinition, ...]] = (
        SectionDefinition(
            key=SECTION_SCHEDULE,
            fields=(CONF_WINDOW_CALENDAR, CONF_ENERGY_METER),
            collapsed=False,
        ),
        SectionDefinition(
            key=SECTION_PRICING,
            fields=(CONF_DEFICIT_PRICE, CONF_OVERAGE_PRICE),
            collapsed=False,
        ),
        SectionDefinition(
            key=SECTION_POWER,
            fields=(CONF_MAX_POWER,),
            collapsed=True,
        ),
    )
