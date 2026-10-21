"""Grid element configuration flows."""

from typing import ClassVar

from custom_components.haeo.core.schema.elements.grid import ELEMENT_TYPE
from custom_components.haeo.core.schema.sections import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
)
from custom_components.haeo.flows.connected_flow import ConnectedElementSubentryFlow
from custom_components.haeo.flows.field_schema import SectionDefinition
from custom_components.haeo.sections import power_limits_section, pricing_section


class GridSubentryFlowHandler(ConnectedElementSubentryFlow):
    """Handle grid element configuration flows."""

    element_type = ELEMENT_TYPE

    sections: ClassVar[tuple[SectionDefinition, ...]] = (
        pricing_section((CONF_PRICE_SOURCE_TARGET, CONF_PRICE_TARGET_SOURCE), collapsed=False),
        power_limits_section(
            (CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE),
            collapsed=True,
        ),
    )
