"""Name an input field as the element's configuration form labels it.

Repair issues and input errors name the field an input reads. Users know a
field by the label their element's form shows, not by its config path, so the
label is read from the integration's ``config_subentries`` translations, which
Home Assistant loads before setting up the integration.
"""

from collections.abc import Mapping

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_cached_translations

from .const import DOMAIN
from .core.data.loader.config_loader import element_inputs
from .core.schema.util import get_nested_config_value_by_path
from .elements import InputFieldPath


def _form_label_key(element_type: str, config_path: InputFieldPath) -> str:
    """Return the translation key of the form label for a config path.

    A section's fields sit under the section, and a list item's fields, edited
    one item per form, sit at the top of the form.
    """
    step = f"component.{DOMAIN}.config_subentries.{element_type}.step.user"
    match config_path:
        case (section, field):
            return f"{step}.sections.{section}.data.{field}"
        case _:
            return f"{step}.data.{config_path[-1]}"


def _list_item_name(config: Mapping[str, object], config_path: InputFieldPath) -> str | None:
    """Return the name of the list item a config path reads, or None for a path outside a list."""
    match config_path:
        case (list_key, index, _field):
            return str(get_nested_config_value_by_path(config, (list_key, index, CONF_NAME)))
        case _:
            return None


def input_field_label(hass: HomeAssistant, entry_id: str, element_name: str, field_path: InputFieldPath) -> str:
    """Return the form label of the field an element's input reads.

    An input fed by another field, such as the trip calendar's away flag, is
    named by that field. A field of a list item, such as a policy rule's price, is named with
    the item. The config path stands in when no label is translated.
    """
    entry = hass.config_entries.async_get_known_entry(entry_id)
    subentry = next(subentry for subentry in entry.subentries.values() if subentry.title == element_name)
    config_path = next(
        element_input.config_path for element_input in element_inputs(subentry.data) if element_input.path == field_path
    )
    translations = async_get_cached_translations(hass, hass.config.language, "config_subentries", DOMAIN)
    label = translations.get(_form_label_key(subentry.subentry_type, config_path))
    if label is None:
        return ".".join(field_path)
    item_name = _list_item_name(subentry.data, config_path)
    if item_name is None:
        return label
    common = async_get_cached_translations(hass, hass.config.language, "common", DOMAIN)
    return common[f"component.{DOMAIN}.common.list_item_field"].format(field=label, item=item_name)
