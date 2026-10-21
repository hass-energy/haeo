"""Solar element configuration flows."""

from typing import ClassVar

from custom_components.haeo.core.schema.elements.solar import CONF_CURTAILMENT, ELEMENT_TYPE
from custom_components.haeo.core.schema.sections import CONF_FORECAST
from custom_components.haeo.flows.connected_flow import ConnectedElementSubentryFlow
from custom_components.haeo.flows.field_schema import SectionDefinition
from custom_components.haeo.flows.sections import curtailment_section, forecast_section


class SolarSubentryFlowHandler(ConnectedElementSubentryFlow):
    """Handle solar element configuration flows."""

    element_type = ELEMENT_TYPE

    sections: ClassVar[tuple[SectionDefinition, ...]] = (
        forecast_section((CONF_FORECAST,), collapsed=False),
        curtailment_section((CONF_CURTAILMENT,), collapsed=True),
    )
