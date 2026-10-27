"""Make inputs unavailable once the readings they hold are too old."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from custom_components.haeo.core.data.input_store import InputStore
    from custom_components.haeo.input_stores import InputStoreMap


class InputHoldExpiry:
    """Expires the readings input stores hold for sources without a reading.

    A store reloads when one of its sources changes, but a source that stays
    without a reading does not change, so nothing would reload the store when
    its held reading grows too old. This follows every store and, when the
    oldest held reading expires, marks the stores holding expired readings
    unavailable and notifies them.
    """

    def __init__(self, hass: HomeAssistant, stores: InputStoreMap) -> None:
        """Initialize over a prebuilt store map."""
        self._hass = hass
        self._stores = list(stores.values())
        self._expires_at: float | None = None
        self._cancel_timer: CALLBACK_TYPE | None = None
        self._unsubs: list[Callable[[], None]] = []

    @callback
    def start(self) -> None:
        """Follow every store, so a store that starts holding a reading schedules its expiry."""
        self._unsubs.extend(store.add_listener(self._schedule) for store in self._stores)

    @callback
    def _schedule(self) -> None:
        """Wait for the earliest held reading to expire, unless already waiting for one that expires sooner."""
        expiries = [expires_at for store in self._stores if (expires_at := store.hold_expires_at) is not None]
        if not expiries:
            return
        expires_at = min(expiries)
        if self._expires_at is not None and self._expires_at <= expires_at:
            return
        self._cancel()
        self._expires_at = expires_at
        self._cancel_timer = async_track_point_in_utc_time(
            self._hass, self._expire, dt_util.utc_from_timestamp(expires_at)
        )

    @callback
    def _expire(self, _now: datetime) -> None:
        """Mark the stores whose held readings expired unavailable, then wait for the next expiry."""
        self._cancel_timer = None
        self._expires_at = None
        expired: list[InputStore] = [store for store in self._stores if store.expire_holds()]
        for store in expired:
            store.notify_listeners()
        self._schedule()

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
