"""Solar element schema definitions."""

from typing import Annotated, Final, Literal

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.field_hints import FieldHint, SectionHints
from custom_components.haeo.core.schema.sections import (
    CONF_CURTAILMENT,
    CONF_FORECAST,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
    ConnectedCommonConfig,
    ConnectedCommonData,
    CurtailmentConfig,
    CurtailmentData,
    ForecastConfig,
    ForecastData,
)

ELEMENT_TYPE = ElementType.SOLAR

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_CURTAILMENT})


class SolarConfigSchema(ConnectedCommonConfig):
    """Solar element configuration as stored in Home Assistant.

    Schema mode contains entity IDs and constant values from the config flow.
    """

    element_type: Literal[ElementType.SOLAR]
    forecast: Annotated[
        ForecastConfig,
        SectionHints(
            {
                CONF_FORECAST: FieldHint(
                    output_type=OutputType.POWER,
                    direction="+",
                    time_series=True,
                ),
            }
        ),
    ]
    curtailment: Annotated[
        CurtailmentConfig,
        SectionHints(
            {
                CONF_CURTAILMENT: FieldHint(
                    output_type=OutputType.STATUS,
                    default_mode="value",
                    default_value=True,
                    force_required=True,
                ),
            }
        ),
    ]


class SolarConfigData(ConnectedCommonData):
    """Solar element configuration with loaded values."""

    element_type: Literal[ElementType.SOLAR]
    forecast: ForecastData
    curtailment: CurtailmentData


__all__ = [
    "CONF_CURTAILMENT",
    "CONF_FORECAST",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_CURTAILMENT",
    "SECTION_FORECAST",
    "SolarConfigData",
    "SolarConfigSchema",
]
