"""Name an input field as the element's configuration form labels it.

Repair issues and input errors name the field an input reads. Users know a
field by the label their element's form shows, not by its config path, so the
label is read from the integration's ``config_subentries`` translations, and a
list item's field by its input entity's name, both of which Home Assistant loads
before setting up the integration.
"""

from collections.abc import Mapping

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_cached_translations

from .const import DOMAIN
from .core.data.loader.config_loader import element_inputs
from .core.schema.util import get_nested_config_value_by_path
from .elements import InputFieldPath

# A list item field's config path: the list, the item's index, and the field
LIST_ITEM_PATH_LENGTH = 3


def _form_label_key(element_type: str, config_path: InputFieldPath) -> str:
    """Return the translation key of the form label for a config path.

    A section's fields sit under the section, and a field at the top of the form under the step.
    """
    step = f"component.{DOMAIN}.config_subentries.{element_type}.step.user"
    match config_path:
        case (section, field):
            return f"{step}.sections.{section}.data.{field}"
        case _:
            return f"{step}.data.{config_path[-1]}"


def _list_item_label(hass: HomeAssistant, config: Mapping[str, object], config_path: InputFieldPath) -> str | None:
    """Return the name of a list item field's input entity, such as a rule's price, or None when it has none.

    A list's items are edited in one element on the form, so a field of an item
    is named as its entity is: by its position, or the item's name when it has one.
    """
    list_key, index, field = config_path
    item = get_nested_config_value_by_path(config, (list_key, index))
    placeholders = {
        "position": str(int(index) + 1),
        "rule_name": str(item.get(CONF_NAME, "")) if isinstance(item, Mapping) else "",
    }
    names = async_get_cached_translations(hass, hass.config.language, "entity", DOMAIN)
    element_type = config.get("element_type")
    for platform in ("number", "switch"):
        name = names.get(f"component.{DOMAIN}.entity.{platform}.{element_type}_{field}.name")
        if name is not None:
            return name.format_map(placeholders)
    return None


def input_field_label(hass: HomeAssistant, entry_id: str, element_name: str, field_path: InputFieldPath) -> str:
    """Return the form label of the field an element's input reads.

    An input fed by another field, such as the trip calendar's away flag, is
    named by that field. A field of a list item, such as a policy rule's price,
    is named as its input entity is. The config path stands in when no label is translated.
    """
    entry = hass.config_entries.async_get_known_entry(entry_id)
    subentry = {subentry.title: subentry for subentry in entry.subentries.values()}[element_name]
    config_path = {element_input.path: element_input.config_path for element_input in element_inputs(subentry.data)}[
        field_path
    ]
    if len(config_path) == LIST_ITEM_PATH_LENGTH:
        label = _list_item_label(hass, {"element_type": subentry.subentry_type, **subentry.data}, config_path)
    else:
        translations = async_get_cached_translations(hass, hass.config.language, "config_subentries", DOMAIN)
        label = translations.get(_form_label_key(subentry.subentry_type, config_path))
    return label if label is not None else ".".join(field_path)
