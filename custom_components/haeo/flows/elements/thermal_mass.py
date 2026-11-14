"""Thermal mass element configuration flows."""

from typing import ClassVar

from custom_components.haeo.core.schema.elements.thermal_mass import (
    CONF_AMBIENT_TEMPERATURE,
    CONF_COMFORT_COST,
    CONF_HEAT_CAPACITY,
    CONF_HEAT_LOSS,
    CONF_HIGHEST_TEMPERATURE,
    CONF_LOWEST_TEMPERATURE,
    CONF_MAX_TEMPERATURE,
    CONF_MIN_TEMPERATURE,
    CONF_TEMPERATURE,
    ELEMENT_TYPE,
    SECTION_COMFORT,
    SECTION_STORAGE,
    SECTION_SURROUNDINGS,
)
from custom_components.haeo.flows.field_schema import SectionDefinition
from custom_components.haeo.flows.sectioned_flow import SectionedElementSubentryFlow


class ThermalMassSubentryFlowHandler(SectionedElementSubentryFlow):
    """Handle thermal mass element configuration flows."""

    element_type = ELEMENT_TYPE

    sections: ClassVar[tuple[SectionDefinition, ...]] = (
        SectionDefinition(
            key=SECTION_STORAGE,
            fields=(CONF_HEAT_CAPACITY, CONF_TEMPERATURE, CONF_LOWEST_TEMPERATURE, CONF_HIGHEST_TEMPERATURE),
            collapsed=False,
        ),
        SectionDefinition(
            key=SECTION_COMFORT, fields=(CONF_MIN_TEMPERATURE, CONF_MAX_TEMPERATURE, CONF_COMFORT_COST), collapsed=False
        ),
        SectionDefinition(key=SECTION_SURROUNDINGS, fields=(CONF_AMBIENT_TEMPERATURE, CONF_HEAT_LOSS), collapsed=False),
    )
