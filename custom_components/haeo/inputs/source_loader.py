"""Load input stores from their source entities, or their constant, over the current horizon."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from custom_components.haeo.inputs.calendar_loader import is_calendar_driven
from custom_components.haeo.inputs.ha_state_machine import HomeAssistantStateMachine

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
        sm = HomeAssistantStateMachine(self._hass)
        changed = [store for store in stores if store.load(sm)]
        for store in changed:
            store.notify_listeners()

    @callback
    def cleanup(self) -> None:
        """Stop following sources and the horizon, and cancel a queued reload."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._pending_reload is not None:
            self._pending_reload.cancel()
            self._pending_reload = None


__all__ = ["SourceInputLoader"]
