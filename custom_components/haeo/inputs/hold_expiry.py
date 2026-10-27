"""Make inputs unavailable once the readings they hold are too old."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import time
from typing import TYPE_CHECKING

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

if TYPE_CHECKING:
    from custom_components.haeo.core.data.input_store import InputStore
    from custom_components.haeo.input_stores import InputStoreMap


class InputHoldExpiry:
    """Expires the readings input stores hold for sources without a reading.

    A store reloads when one of its sources changes, but a source that stays
    without a reading does not change, so nothing would reload the store when
    its held reading grows too old. This follows every store and, when the
    earliest held reading expires, marks the stores holding expired readings
    unavailable and notifies them.
    """

    def __init__(self, hass: HomeAssistant, stores: InputStoreMap) -> None:
        """Initialize over a prebuilt store map."""
        self._hass = hass
        self._stores = list(stores.values())
        # When the timer fires, on the monotonic clock the stores' expiries use
        self._expires_at: float | None = None
        self._cancel_timer: CALLBACK_TYPE | None = None
        self._unsubs: list[Callable[[], None]] = []

    @callback
    def start(self) -> None:
        """Follow every store, so a store that starts holding a reading schedules its expiry."""
        self._unsubs.extend(store.add_listener(self._follower(store)) for store in self._stores)

    def _follower(self, store: InputStore) -> Callable[[], None]:
        """Return a listener that schedules the store's expiry when it changes."""

        @callback
        def _store_changed() -> None:
            if (expires_at := store.hold_expires_at) is not None:
                self._schedule(expires_at)

        return _store_changed

    @callback
    def _schedule(self, expires_at: float) -> None:
        """Wait until ``expires_at``, unless already waiting for an expiry no later than it.

        A timer kept for a hold that has since ended fires to no effect, then
        waits for the next expiry.
        """
        if self._expires_at is not None and self._expires_at <= expires_at:
            return
        self._cancel()
        self._expires_at = expires_at
        self._cancel_timer = async_call_later(self._hass, max(0.0, expires_at - time.monotonic()), self._expire)

    @callback
    def _expire(self, _now: datetime) -> None:
        """Mark the stores whose held readings expired unavailable, then wait for the next expiry."""
        self._cancel_timer = None
        self._expires_at = None
        expired = [store for store in self._stores if store.expire_holds()]
        for store in expired:
            store.notify_listeners()
        expiries = [expires_at for store in self._stores if (expires_at := store.hold_expires_at) is not None]
        if expiries:
            self._schedule(min(expiries))

    def _cancel(self) -> None:
        """Stop waiting for an expiry, if waiting for one."""
        if self._cancel_timer is not None:
            self._cancel_timer()
            self._cancel_timer = None
        self._expires_at = None

    @callback
    def cleanup(self) -> None:
        """Stop following the stores and waiting for an expiry."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        self._cancel()


__all__ = ["InputHoldExpiry"]
