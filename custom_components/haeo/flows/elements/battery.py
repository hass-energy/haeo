"""Battery element configuration flows."""

from typing import ClassVar

from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_CHARGE_COST,
    CONF_CHARGE_LIMIT_COST,
    CONF_DISCHARGE_COST,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_SALVAGE_VALUE,
    ELEMENT_TYPE,
    SECTION_ADVANCED,
    SECTION_LIMITS,
    SECTION_STORAGE,
)
from custom_components.haeo.core.schema.sections import CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE
from custom_components.haeo.flows.connected_flow import ConnectedElementSubentryFlow
from custom_components.haeo.flows.field_schema import SectionDefinition
from custom_components.haeo.sections import efficiency_section, power_limits_section, pricing_section


class BatterySubentryFlowHandler(ConnectedElementSubentryFlow):
    """Handle battery element configuration flows."""

    element_type = ELEMENT_TYPE

    sections: ClassVar[tuple[SectionDefinition, ...]] = (
        SectionDefinition(key=SECTION_STORAGE, fields=(CONF_CAPACITY, CONF_INITIAL_CHARGE_PERCENTAGE), collapsed=False),
        SectionDefinition(
            key=SECTION_LIMITS,
            fields=(
                CONF_MIN_CHARGE_PERCENTAGE,
                CONF_MAX_CHARGE_PERCENTAGE,
            ),
            collapsed=False,
        ),
        power_limits_section((CONF_MAX_POWER_TARGET_SOURCE, CONF_MAX_POWER_SOURCE_TARGET), collapsed=False),
        pricing_section((CONF_SALVAGE_VALUE, CONF_CHARGE_COST, CONF_DISCHARGE_COST), collapsed=False),
        efficiency_section((CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE), collapsed=True),
        SectionDefinition(key=SECTION_ADVANCED, fields=(CONF_CHARGE_LIMIT_COST,), collapsed=True),
    )
