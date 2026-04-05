"""Plot metadata helpers shared by HAEO entities."""

from custom_components.haeo.core.model import OutputType

PLOT_STREAM_KEY = "plot_stream"
PLOT_PRIORITY_KEY = "plot_priority"
SOURCE_ROLE_KEY = "source_role"

SOURCE_ROLE_OUTPUT = "output"
SOURCE_ROLE_FORECAST = "forecast"
SOURCE_ROLE_LIMIT = "limit"

_STREAM_PRIORITY_BY_KEY: dict[tuple[str, str], tuple[str, int]] = {
    ("load", "-"): ("load_consumption", 1),
    ("solar", "+"): ("solar_production", 2),
    ("battery", "-"): ("battery_charge", 3),
    ("battery", "+"): ("battery_discharge", 4),
    ("grid", "+"): ("grid_export", 5),
    ("grid", "-"): ("grid_import", 6),
}


def classify_source_role(config_mode: str | None, field_name: str | None) -> str:
    """Classify whether stream data is output, forecast, or limit."""
    if config_mode is None:
        return SOURCE_ROLE_OUTPUT
    return SOURCE_ROLE_FORECAST if field_name == "forecast" else SOURCE_ROLE_LIMIT


def build_plot_metadata(
    *,
    element_type: str,
    output_type: OutputType | str,
    direction: str | None,
    source_role: str,
) -> dict[str, str | int]:
    """Return plot metadata for a stream when it is relevant to chart ordering."""
    if str(output_type) != OutputType.POWER:
        return {}
    if direction not in {"+", "-"}:
        return {}
    stream = _STREAM_PRIORITY_BY_KEY.get((element_type, direction))
    if stream is None:
        return {}
    stream_name, priority = stream
    return {
        SOURCE_ROLE_KEY: source_role,
        PLOT_STREAM_KEY: stream_name,
        PLOT_PRIORITY_KEY: priority,
    }
