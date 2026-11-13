"""Load input stores from their source entities, or their constant, over the current horizon."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from custom_components.haeo.inputs.calendar_loader import is_calendar_driven
from custom_components.haeo.inputs.ha_state_machine import HomeAssistantStateMachine
from custom_components.haeo.inputs.recorded_reading import async_last_recorded_reading

if TYPE_CHECKING:
    from homeassistant.core import Event
    from homeassistant.helpers.event import EventStateChangedData

    from custom_components.haeo.core.data.input_store import InputStore
    from custom_components.haeo.horizon import HorizonManager
    from custom_components.haeo.input_stores import InputStoreMap


class SourceInputLoader:
    """Keeps every input without a calendar source loaded over the current horizon.

    The loader, not the input entities, loads the stores, so an input loads
    whether or not its entity is enabled. It loads every store when it starts
    and when the horizon moves, and reloads a store when one of its sources
    changes. Calendar inputs are loaded by the calendar loader instead.

    A source that has no reading and no last reading in its stores, as after a
    restart, has its last recorded state with a reading looked up once. The
    stores reading it hold that state from when it was last reported, then
    reload.
    """

    def __init__(self, hass: HomeAssistant, stores: InputStoreMap, horizon_manager: HorizonManager) -> None:
        """Initialize the loader over a prebuilt store map."""
        self._hass = hass
        self._horizon_manager = horizon_manager
        self._stores = [store for store in stores.values() if not is_calendar_driven(store)]
        self._stores_by_source: dict[str, list[InputStore]] = {}
        for store in self._stores:
            for entity_id in store.source_entity_ids:
                self._stores_by_source.setdefault(entity_id, []).append(store)
        # Stores waiting for the queued reload, in the order their sources changed
        self._pending: dict[InputStore, None] = {}
        self._pending_reload: asyncio.Task[None] | None = None
        # Sources whose recorded reading has been looked up, and the lookups still running
        self._looked_up: set[str] = set()
        self._lookups: set[asyncio.Task[None]] = set()
        self._unsubs: list[Callable[[], None]] = []

    @callback
    def start(self) -> None:
        """Load every store, then follow their sources and the horizon."""
        self._load(self._stores)
        if self._stores_by_source:
            self._unsubs.append(
                async_track_state_change_event(self._hass, sorted(self._stores_by_source), self._on_source_change)
            )
        self._unsubs.append(self._horizon_manager.subscribe(lambda: self._load(self._stores)))

    @callback
    def _on_source_change(self, event: Event[EventStateChangedData]) -> None:
        """Queue a reload of the stores that read the changed entity.

        Forecast integrations write all of their entities in a single pass, and
        a store reads every one of its sources on each load. Deferring the
        reload to the next event loop iteration lets every change in that pass
        arrive first, so they share one reload.
        """
        self._pending.update(dict.fromkeys(self._stores_by_source[event.data["entity_id"]]))
        if self._pending_reload is None:
            self._pending_reload = self._hass.async_create_task(self._async_reload_pending(), eager_start=False)

    async def _async_reload_pending(self) -> None:
        """Reload the queued stores, letting later source changes queue another reload."""
        self._pending_reload = None
        stores, self._pending = self._pending, {}
        self._load(stores)

    def _load(self, stores: Iterable[InputStore]) -> None:
        """Load the stores, then notify the ones that changed.

        Every store loads before any store notifies its listeners, so a
        listener never runs while another store still holds the previous horizon.
        """
        stores = list(stores)
        sm = HomeAssistantStateMachine(self._hass)
        changed = [store for store in stores if store.load(sm)]
        for store in changed:
            store.notify_listeners()
        unseeded = {eid for store in stores for eid in store.sources_without_last_reading} - self._looked_up
        if unseeded:
            self._looked_up |= unseeded
            task = self._hass.async_create_task(self._async_seed(sorted(unseeded)), eager_start=False)
            self._lookups.add(task)
            task.add_done_callback(self._lookups.discard)

    async def _async_seed(self, entity_ids: list[str]) -> None:
        """Seed the stores reading each source with its last recorded reading, then reload them."""
        recorded = await asyncio.gather(*(async_last_recorded_reading(self._hass, eid) for eid in entity_ids))
        seeded = {
            store: None
            for eid, state in zip(entity_ids, recorded, strict=True)
            if state is not None
            for store in self._stores_by_source[eid]
            if store.seed_reading(eid, state, state.last_reported_timestamp)
        }
        self._load(seeded)

    @callback
    def cleanup(self) -> None:
        """Stop following sources and the horizon, and cancel a queued reload and any recorder lookups."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._pending_reload is not None:
            self._pending_reload.cancel()
            self._pending_reload = None
        for task in self._lookups:
            task.cancel()


__all__ = ["SourceInputLoader"]
