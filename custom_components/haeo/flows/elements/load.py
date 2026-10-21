"""Load element configuration flows."""

from typing import ClassVar

from custom_components.haeo.const import URL_HAFO
from custom_components.haeo.core.schema.elements.load import CONF_CONSUMPTION_COST, ELEMENT_TYPE
from custom_components.haeo.core.schema.sections import CONF_CURTAILMENT, CONF_FORECAST, SECTION_CURTAILMENT
from custom_components.haeo.flows.connected_flow import ConnectedElementSubentryFlow
from custom_components.haeo.flows.field_schema import SectionDefinition
from custom_components.haeo.sections import forecast_section


class LoadSubentryFlowHandler(ConnectedElementSubentryFlow):
    """Handle load element configuration flows."""

    element_type = ELEMENT_TYPE
    description_placeholders: ClassVar[dict[str, str] | None] = {"hafo_url": URL_HAFO}

    sections: ClassVar[tuple[SectionDefinition, ...]] = (
        forecast_section((CONF_FORECAST,), collapsed=False),
        SectionDefinition(key=SECTION_CURTAILMENT, fields=(CONF_CURTAILMENT, CONF_CONSUMPTION_COST), collapsed=True),
    )
