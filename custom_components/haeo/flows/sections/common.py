"""Flow builders for common configuration fields."""

from homeassistant.helpers.selector import TextSelector, TextSelectorConfig
import voluptuous as vol

from custom_components.haeo.core.const import CONF_NAME


def build_common_fields() -> dict[str, tuple[vol.Marker, object]]:
    """Build the name field every element's form starts with."""
    return {
        CONF_NAME: (
            vol.Required(CONF_NAME),
            vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
        ),
    }


__all__ = [
    "build_common_fields",
]
