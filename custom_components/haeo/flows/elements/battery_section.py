"""Battery section element configuration flows."""

from typing import ClassVar

from custom_components.haeo.core.schema.elements.battery_section import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE,
    ELEMENT_TYPE,
    SECTION_STORAGE,
)
from custom_components.haeo.flows.field_schema import SectionDefinition
from custom_components.haeo.flows.sectioned_flow import SectionedElementSubentryFlow


class BatterySectionSubentryFlowHandler(SectionedElementSubentryFlow):
    """Handle battery section element configuration flows."""

    element_type = ELEMENT_TYPE

    sections: ClassVar[tuple[SectionDefinition, ...]] = (
        SectionDefinition(key=SECTION_STORAGE, fields=(CONF_CAPACITY, CONF_INITIAL_CHARGE), collapsed=False),
    )
