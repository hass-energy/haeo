"""Flow builders for forecast configuration sections."""

from custom_components.haeo.core.schema.sections.forecast import CONF_FORECAST, SECTION_FORECAST
from custom_components.haeo.flows.field_schema import SectionDefinition


def forecast_section(fields: tuple[str, ...] = (CONF_FORECAST,), *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard forecast section definition."""
    return SectionDefinition(key=SECTION_FORECAST, fields=fields, collapsed=collapsed)


__all__ = [
    "forecast_section",
]
