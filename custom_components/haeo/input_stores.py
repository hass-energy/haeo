"""Build and back input stores from configuration.

This is the integration-layer glue that turns element subentries into the set
of :class:`InputStore` instances used across the system. Each store is bound to
a :class:`SubentryStorage` so edits persist back to the originating subentry.

Stores are built once during setup and registered on the runtime data. Home
Assistant entities then wrap these stores for display, and the coordinator
reads their resolved values to feed the optimization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from custom_components.haeo.core.data.input_store import InputStore, create_input_store
from custom_components.haeo.core.schema import is_none_value
from custom_components.haeo.core.schema.field_hints import FieldHint
from custom_components.haeo.elements import (
    InputFieldPath,
    get_input_fields,
    get_list_input_fields,
    get_nested_config_value_by_path,
    is_element_config_schema,
    iter_input_field_paths,
)
from custom_components.haeo.util import async_update_subentry_value

if TYPE_CHECKING:
    from custom_components.haeo import HaeoConfigEntry
    from custom_components.haeo.elements.input_fields import InputFieldInfo
    from custom_components.haeo.horizon import HorizonManager

type InputStoreKey = tuple[str, InputFieldPath]
type InputStoreMap = dict[InputStoreKey, InputStore]


class SubentryStorage:
    """Persistence binding backing an input store to a config subentry field.

    Reads always resolve against the live subentry data because
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

    def read(self) -> Any:
        """Return the currently persisted schema value, or None."""
        subentry = self._config_entry.subentries.get(self._subentry_id)
        if subentry is None:
            return None
        return get_nested_config_value_by_path(subentry.data, self._field_path)

    async def write(self, value: Any) -> None:
        """Persist a new schema value to the subentry."""
        subentry = self._config_entry.subentries[self._subentry_id]
        await async_update_subentry_value(
            self._hass,
            self._config_entry,
            subentry,
            field_path=self._field_path,
            value=value,
        )


def _hint_from_field_info(field_info: InputFieldInfo[Any]) -> FieldHint:
    """Build the resolver field hint from an input field's metadata."""
    return FieldHint(
        output_type=field_info.output_type,
        direction=field_info.direction,
        time_series=field_info.time_series,
        boundaries=field_info.boundaries,
    )


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

    for subentry in config_entry.subentries.values():
        if not is_element_config_schema(subentry.data):
            continue

        all_fields = {
            **get_input_fields(subentry.data),
            **get_list_input_fields(subentry.data),
        }

        for field_path, field_info in iter_input_field_paths(all_fields):
            config_value = get_nested_config_value_by_path(subentry.data, field_path)
            if config_value is None or is_none_value(config_value):
                continue

            storage = SubentryStorage(hass, config_entry, subentry.subentry_id, field_path)
            store = create_input_store(
                storage=storage,
                hint=_hint_from_field_info(field_info),
                get_forecast_timestamps=horizon_manager.get_forecast_timestamps,
            )
            stores[(subentry.title, field_path)] = store

    return stores


__all__ = ["InputStoreKey", "InputStoreMap", "SubentryStorage", "build_input_stores"]
