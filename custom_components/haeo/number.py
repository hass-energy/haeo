"""Number platform for HAEO input entities."""

import logging

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo import HaeoConfigEntry, HaeoRuntimeData
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements.policy import CONF_PRICE, CONF_RULES
from custom_components.haeo.elements import (
    get_input_fields,
    get_list_input_fields,
    get_surfaced_input_fields,
    get_surfaced_price_hints,
    is_element_config_schema,
    iter_input_field_paths,
)
from custom_components.haeo.entities.device import get_or_create_element_device
from custom_components.haeo.entities.haeo_number import HaeoInputNumber
from custom_components.haeo.flows.surfaced_policy import find_policy_subentry, find_surfaced_rule
from custom_components.haeo.horizon import HorizonManager

_LOGGER = logging.getLogger(__name__)


def _build_surfaced_mirror_entities(
    config_entry: HaeoConfigEntry,
    subentry: ConfigSubentry,
    element_type: str,
    device_entry: DeviceEntry,
    runtime_data: HaeoRuntimeData,
    horizon_manager: HorizonManager,
) -> list[HaeoInputNumber]:
    """Build mirror entities for an element's surfaced policy prices.

    Surfaced prices (e.g. battery charge/discharge cost) live as rules in the
    single policy subentry, so they already appear as entities on the policy
    device. This creates additional entities on the element's own device that
    wrap the same store, so editing either updates the one stored value.
    """
    surfaced_hints = get_surfaced_price_hints(element_type)
    if not surfaced_hints:
        return []

    policy_subentry = find_policy_subentry(config_entry)
    if policy_subentry is None:
        return []

    rules = list(policy_subentry.data.get(CONF_RULES, []))
    surfaced_fields = get_surfaced_input_fields(element_type)

    entities: list[HaeoInputNumber] = []
    for field_name, hint in surfaced_hints.items():
        field_info = surfaced_fields.get(field_name)
        if field_info is None:
            continue

        source = None if hint.source_is_wildcard else [subentry.title]
        target = [subentry.title] if hint.source_is_wildcard else None
        rule_index = find_surfaced_rule(rules, source=source, target=target)
        if rule_index is None:
            continue

        store_key = (policy_subentry.title, (CONF_RULES, str(rule_index), CONF_PRICE))
        store = runtime_data.input_stores.get(store_key)
        if store is None:
            continue

        entities.append(
            HaeoInputNumber(
                config_entry=config_entry,
                subentry=subentry,
                field_info=field_info,
                field_path=(field_name,),
                device_entry=device_entry,
                horizon_manager=horizon_manager,
                store=store,
                negate=hint.negate,
            )
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAEO number entities from a config entry.

    Creates number entities for each numeric input field in element subentries.
    These entities serve as configurable inputs for the optimization model.
    """
    # Runtime data must be set by __init__.py before platforms are set up
    if config_entry.runtime_data is None:
        msg = "Runtime data not set - integration setup incomplete"
        raise RuntimeError(msg)

    runtime_data = config_entry.runtime_data
    horizon_manager = runtime_data.horizon_manager

    entities: list[HaeoInputNumber] = []

    for subentry in config_entry.subentries.values():
        if not is_element_config_schema(subentry.data):
            continue
        element_config = subentry.data
        element_type = element_config[CONF_ELEMENT_TYPE]

        # Get input field definitions for this element type (section-based)
        input_fields = get_input_fields(element_config)

        # Also get dynamic input fields from list-based config structures
        list_input_fields = get_list_input_fields(element_config)

        # Combine all number fields from both sources
        all_fields = {**input_fields, **list_input_fields}

        # Filter to only number fields (by entity description class name)
        # Note: isinstance doesn't work due to Home Assistant's frozen_dataclass_compat wrapper
        number_fields = [
            (field_path, field_info)
            for field_path, field_info in iter_input_field_paths(all_fields)
            if type(field_info.entity_description).__name__ == "NumberEntityDescription"
        ]

        surfaced_hints = get_surfaced_price_hints(element_type)
        if not number_fields and not surfaced_hints:
            continue

        # Get or create device using centralized device creation
        # Input entities go on the main device (element_type matches device_name)
        device_entry = get_or_create_element_device(hass, config_entry, subentry, element_type)

        for field_path, field_info in number_fields:
            # Only create entities for fields that have a prebuilt store
            # (none/disabled fields are skipped during store construction)
            store = runtime_data.input_stores.get((subentry.title, field_path))
            if store is None:
                continue

            entity = HaeoInputNumber(
                config_entry=config_entry,
                subentry=subentry,
                field_info=field_info,
                field_path=field_path,
                device_entry=device_entry,
                horizon_manager=horizon_manager,
                store=store,
            )
            entities.append(entity)

        entities.extend(
            _build_surfaced_mirror_entities(
                config_entry,
                subentry,
                element_type,
                device_entry,
                runtime_data,
                horizon_manager,
            )
        )

    if entities:
        _LOGGER.debug("Creating %d number entities for HAEO inputs", len(entities))
        async_add_entities(entities)
    else:
        _LOGGER.debug("No number entities to create for entry %s", config_entry.entry_id)
