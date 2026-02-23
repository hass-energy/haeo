"""Load element schema definitions."""

from typing import Annotated, Final, Literal, TypedDict

from custom_components.haeo.model.const import OutputType
from custom_components.haeo.schema.elements import ElementType
from custom_components.haeo.schema.field_hints import FieldHint, SectionHints
from custom_components.haeo.sections import (
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
    SECTION_PRICING,
    ConnectedCommonConfig,
    ConnectedCommonData,
    CurtailmentConfig,
    CurtailmentData,
    ForecastConfig,
    ForecastData,
    PricingConfig,
    PricingData,
)

ELEMENT_TYPE = ElementType.LOAD

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_CURTAILMENT, CONF_PRICE_TARGET_SOURCE})


class LoadConfigSchema(TypedDict):
    """Load element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.LOAD]
    common: ConnectedCommonConfig
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
    pricing: Annotated[
        PricingConfig,
        SectionHints(
            {
                CONF_PRICE_TARGET_SOURCE: FieldHint(
                    output_type=OutputType.PRICE,
                    direction="+",
                    time_series=True,
                    default_value=0.0,
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
                    default_value=False,
                    force_required=True,
                ),
            }
        ),
    ]


class LoadConfigData(TypedDict):
    """Load element configuration with loaded values."""

    element_type: Literal[ElementType.LOAD]
    common: ConnectedCommonData
    forecast: ForecastData
    pricing: PricingData
    curtailment: CurtailmentData


__all__ = [
    "CONF_CURTAILMENT",
    "CONF_FORECAST",
    "CONF_PRICE_TARGET_SOURCE",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_COMMON",
    "SECTION_CURTAILMENT",
    "SECTION_FORECAST",
    "SECTION_PRICING",
    "LoadConfigData",
    "LoadConfigSchema",
]
