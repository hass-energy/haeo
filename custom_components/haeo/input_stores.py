"""Build and back input stores from configuration.

This is the integration-layer glue that turns element subentries into the set
of :class:`InputStore` instances used across the system. Each store is bound to
a :class:`SubentryStorage` so edits persist back to the originating subentry.

Stores are built once during setup and registered on the runtime data. Home
Assistant entities then wrap these stores for display, and the coordinator
reads their resolved values to feed the optimization.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant

from custom_components.haeo.core.adapters.reserve import resolve_reserves
from custom_components.haeo.core.data.input_store import InputMode, InputStore, create_input_store
from custom_components.haeo.core.data.loader.config_loader import load_element_config_from_values
from custom_components.haeo.core.data.util.input_values import InputError
from custom_components.haeo.core.schema import is_none_value
from custom_components.haeo.core.schema.elements import ElementConfigSchema
from custom_components.haeo.core.schema.field_hints import FieldHint
from custom_components.haeo.core.schema.surfaced_policy import negated_price_paths
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
    from custom_components.haeo.elements.input_fields import AnyInputFieldInfo
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

    def read(self) -> object:
        """Return the currently persisted schema value, or None."""
        subentry = self._config_entry.subentries.get(self._subentry_id)
        if subentry is None:
            return None
        return get_nested_config_value_by_path(subentry.data, self._field_path)

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


class ReserveResolver:
    """Keeps derived reserve stores up to date with the stores they are computed from.

    Whenever a source store changes, every element's config is assembled from
    the source stores and the reserve is recomputed. Sources still loading for
    an older horizon are waited for, so the reserve always matches the horizon
    of the values it was computed from.
    """

    def __init__(
        self,
        participants: Mapping[str, ElementConfigSchema],
        stores: InputStoreMap,
        get_forecast_timestamps: Callable[[], tuple[float, ...]],
    ) -> None:
        """Initialize the resolver."""
        self._participants = participants
        self._derived = {key: store for key, store in stores.items() if store.mode == InputMode.DERIVED}
        self._sources = {key: store for key, store in stores.items() if store.mode != InputMode.DERIVED}
        self._get_forecast_timestamps = get_forecast_timestamps

    def start(self) -> None:
        """Recompute now and whenever a source store changes."""
        for store in self._sources.values():
            store.add_listener(self.update)
        self.update()

    def update(self) -> None:
        """Recompute the derived stores once every source store holds a value for the current horizon."""
        forecast_timestamps = self._get_forecast_timestamps()
        if not all(
            store.available and (not store.time_series or store.forecast_timestamps == forecast_timestamps)
            for store in self._sources.values()
        ):
            return

        loaded = {
            name: load_element_config_from_values(
                name,
                config,
                {path: store.value for (element, path), store in self._sources.items() if element == name},
                forecast_timestamps,
            )
            for name, config in self._participants.items()
        }
        for key, value in resolve_reserves(self._participants, loaded, forecast_timestamps).items():
            self._derived[key].set_derived(value, forecast_timestamps)


def _hint_from_field_info(field_info: AnyInputFieldInfo) -> FieldHint:
    """Build the resolver field hint from an input field's metadata."""
    return FieldHint(
        output_type=field_info.output_type,
        direction=field_info.direction,
        time_series=field_info.time_series,
        boundaries=field_info.boundaries,
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

        all_fields = {
            **get_input_fields(subentry.data),
            **get_list_input_fields(subentry.data),
        }
        subentry_negated_paths = negated_paths.get(subentry.title, frozenset())

        for field_path, field_info in iter_input_field_paths(all_fields):
            config_value = get_nested_config_value_by_path(subentry.data, field_path)
            if config_value is None or is_none_value(config_value):
                continue

            storage = SubentryStorage(hass, config_entry, subentry.subentry_id, field_path)
            store = create_input_store(
                storage=storage,
                hint=_hint_from_field_info(field_info),
                get_forecast_timestamps=horizon_manager.get_forecast_timestamps,
                negate=field_path in subentry_negated_paths,
            )
            stores[(subentry.title, field_path)] = store

    if any(store.mode == InputMode.DERIVED for store in stores.values()):
        participants = {
            subentry.title: subentry.data
            for subentry in config_entry.subentries.values()
            if is_element_config_schema(subentry.data)
        }
        ReserveResolver(participants, stores, horizon_manager.get_forecast_timestamps).start()

    return stores


__all__ = [
    "InputStoreKey",
    "InputStoreMap",
    "ReserveResolver",
    "SubentryStorage",
    "build_input_stores",
    "input_error_placeholders",
]
