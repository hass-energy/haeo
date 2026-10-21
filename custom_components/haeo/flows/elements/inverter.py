"""Inverter element configuration flows."""

from typing import ClassVar

from custom_components.haeo.core.schema.elements.inverter import ELEMENT_TYPE
from custom_components.haeo.core.schema.sections import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
)
from custom_components.haeo.flows.connected_flow import ConnectedElementSubentryFlow
from custom_components.haeo.flows.field_schema import SectionDefinition
from custom_components.haeo.sections import efficiency_section, power_limits_section


class InverterSubentryFlowHandler(ConnectedElementSubentryFlow):
    """Handle inverter element configuration flows."""

    element_type = ELEMENT_TYPE

    sections: ClassVar[tuple[SectionDefinition, ...]] = (
        power_limits_section(
            (CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE),
            collapsed=False,
        ),
        efficiency_section(
            (CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE),
            collapsed=True,
        ),
    )
