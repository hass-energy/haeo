"""Build and back input stores from configuration.

This is the integration-layer glue that turns element subentries into the set
of :class:`InputStore` instances used across the system. Each store is bound to
a :class:`SubentryStorage` so edits persist back to the originating subentry.

Stores are built once during setup and registered on the runtime data. Home
Assistant entities then wrap these stores for display, and the coordinator
reads their resolved values to feed the optimization.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_INPUT_HOLD_SECONDS, DEFAULT_INPUT_HOLD_SECONDS, HUB_SECTION_ADVANCED
from custom_components.haeo.core.data.input_store import InputStore, create_input_store
from custom_components.haeo.core.data.loader.config_loader import element_inputs, input_value
from custom_components.haeo.core.data.util.input_values import InputError
from custom_components.haeo.core.schema.elements.conformance import is_element_config_schema
from custom_components.haeo.core.schema.surfaced_policy import negated_price_paths
from custom_components.haeo.elements import InputFieldPath
from custom_components.haeo.util import async_update_subentry_value

if TYPE_CHECKING:
    from custom_components.haeo import HaeoConfigEntry
    from custom_components.haeo.horizon import HorizonManager

type InputStoreKey = tuple[str, InputFieldPath]
type InputStoreMap = dict[InputStoreKey, InputStore]


class SubentryStorage:
    """Persistence binding backing an input store to a config subentry field.

    Writes always resolve against the live subentry because
    ``async_update_subentry_value`` replaces the underlying mapping, making any
    cached reference stale.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: HaeoConfigEntry,
        subentry_id: str,
        field_path: InputFieldPath,
    ) -> None:
        """Initialize the storage binding."""
        self._hass = hass
        self._config_entry = config_entry
        self._subentry_id = subentry_id
        self._field_path = field_path

    async def write(self, value: object) -> None:
        """Persist a new schema value to the subentry."""
        subentry = self._config_entry.subentries[self._subentry_id]
        await async_update_subentry_value(
            self._hass,
            self._config_entry,
            subentry,
            field_path=self._field_path,
            value=value,
        )


def input_error_placeholders(key: InputStoreKey, error: InputError, store: InputStore) -> dict[str, str]:
    """Return translation placeholders for a rejected input.

    Adds the element, field, and source entities to the placeholders the
    rejecting check supplied, so every input error message can name them.
    """
    element_name, field_path = key
    return {
        "element": element_name,
        "field": ".".join(field_path),
        "entities": ", ".join(store.source_entity_ids),
        **error.translation_placeholders,
    }


def raise_for_rejected_input(input_stores: InputStoreMap, error_type: type[HomeAssistantError]) -> None:
    """Raise ``error_type`` naming the first input that rejected its source's value, if one did."""
    for key, store in input_stores.items():
        if (error := store.error) is not None:
            raise error_type(
                translation_domain=DOMAIN,
                translation_key=error.translation_key,
                translation_placeholders=input_error_placeholders(key, error, store),
            )


def unavailable_input_sources(
    input_stores: InputStoreMap, is_unavailable: Callable[[InputStore], bool]
) -> dict[InputStoreKey, tuple[str, ...]]:
    """Return the sources to name for each input ``is_unavailable`` picks.

    Names the sources with no reading, or every source when they all have one
    but the input still could not load. Inputs that rejected their source's
    value report that error instead, so they are left out.
    """
    return {
        key: store.unavailable_sources or tuple(store.source_entity_ids)
        for key, store in input_stores.items()
        if store.error is None and is_unavailable(store)
    }


def unavailable_input_placeholders(key: InputStoreKey, entities: tuple[str, ...]) -> dict[str, str]:
    """Return translation placeholders naming an unavailable input and its sources."""
    element_name, field_path = key
    return {"element": element_name, "field": ".".join(field_path), "entities": ", ".join(entities)}


def build_input_stores(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    horizon_manager: HorizonManager,
) -> InputStoreMap:
    """Build the full set of input stores from a config entry's subentries.

    Iterates every configured input field across element subentries and creates
    a store bound to the originating subentry. Disabled (none) and absent fields
    are skipped, mirroring entity creation. Every store holds a source's last
    reading for as long as the hub's input hold setting allows.
    """
    stores: InputStoreMap = {}
    hold_seconds = float(
        config_entry.data.get(HUB_SECTION_ADVANCED, {}).get(CONF_INPUT_HOLD_SECONDS, DEFAULT_INPUT_HOLD_SECONDS)
    )

    negated_paths = negated_price_paths(
        {subentry.title: subentry.data for subentry in config_entry.subentries.values()}
    )

    for subentry in config_entry.subentries.values():
        if not is_element_config_schema(subentry.data):
            continue

        subentry_negated_paths = negated_paths.get(subentry.title, frozenset())

        for element_input in element_inputs(subentry.data):
            value = input_value(subentry.data, element_input)
            if value is None:
                continue

            storage = SubentryStorage(hass, config_entry, subentry.subentry_id, element_input.config_path)
            store = create_input_store(
                value=value,
                storage=storage,
                hint=element_input.hint,
                get_forecast_timestamps=horizon_manager.get_forecast_timestamps,
                negate=element_input.path in subentry_negated_paths,
                hold_seconds=hold_seconds,
            )
            stores[(subentry.title, element_input.path)] = store

    return stores


__all__ = [
    "InputStoreKey",
    "InputStoreMap",
    "SubentryStorage",
    "build_input_stores",
    "input_error_placeholders",
    "raise_for_rejected_input",
    "unavailable_input_placeholders",
    "unavailable_input_sources",
]
