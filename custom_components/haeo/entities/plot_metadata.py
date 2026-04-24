"""Source role metadata helpers shared by HAEO entities."""

SOURCE_ROLE_KEY = "source_role"

SOURCE_ROLE_OUTPUT = "output"
SOURCE_ROLE_FORECAST = "forecast"
SOURCE_ROLE_LIMIT = "limit"


def classify_source_role(config_mode: str | None, field_name: str | None) -> str:
    """Classify whether stream data is output, forecast, or limit."""
    if config_mode is None:
        return SOURCE_ROLE_OUTPUT
    return SOURCE_ROLE_FORECAST if field_name == "forecast" else SOURCE_ROLE_LIMIT
