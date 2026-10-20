"""Build and back input stores from configuration.

This is the integration-layer glue that turns element subentries into the set
of :class:`InputStore` instances used across the system. Each store is bound to
a :class:`SubentryStorage` so edits persist back to the originating subentry.

Stores are built once during setup and registered on the runtime data. Home
Assistant entities then wrap these stores for display, and the coordinator
reads their resolved values to feed the optimization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant

from custom_components.haeo.core.data.input_store import InputStore, create_input_store
from custom_components.haeo.core.data.loader.config_loader import element_inputs, input_value
from custom_components.haeo.core.data.util.input_values import InputError
from custom_components.haeo.core.schema.surfaced_policy import negated_price_paths
from custom_components.haeo.elements import InputFieldPath, is_element_config_schema
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


def build_input_stores(
    hass: HomeAssistant,
    config_entry: HaeoConfigEntry,
    horizon_manager: HorizonManager,
) -> InputStoreMap:
    """Build the full set of input stores from a config entry's subentries.

    Iterates every configured input field across element subentries and creates
    a store bound to the originating subentry. Disabled (none) and absent fields
    are skipped, mirroring entity creation.
    """
    stores: InputStoreMap = {}

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
            )
            stores[(subentry.title, element_input.path)] = store

    return stores


__all__ = ["InputStoreKey", "InputStoreMap", "SubentryStorage", "build_input_stores", "input_error_placeholders"]
