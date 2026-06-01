"""In-process Home Assistant runner for guide tests.

This module provides a way to run Home Assistant entirely in-process with
an HTTP server on an ephemeral port, allowing browser automation via Playwright.

The key insight is that we can:
1. Create a HomeAssistant instance with a minimal temp config directory
2. Set up the HTTP, frontend, and auth components programmatically
3. Load entity states directly via hass.states.async_set()
4. Run the event loop in a background thread
5. Access the HA instance from the main thread for Playwright automation
6. Pre-create the dev user and register a trusted_networks provider so loopback
   browsers auto-login without minting tokens (shared with ``uv run sim``)

This avoids needing config files, YAML, or packages - just load states from JSON.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Generator
from contextlib import closing, contextmanager
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import socket
import tempfile
import threading
from typing import Any
import warnings

from homeassistant import loader
from homeassistant.auth import auth_manager_from_config
from homeassistant.auth.models import Credentials
from homeassistant.config_entries import ConfigEntries, ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import category_registry as cr
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity, translation
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import floor_registry as fr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers import label_registry as lr
from homeassistant.helpers import restore_state as rs
from homeassistant.setup import async_setup_component
from playwright.sync_api import BrowserContext

PROJECT_ROOT = Path(__file__).parent.parent
_LOGGER = logging.getLogger(__name__)

# Loopback networks the trusted_networks auth provider auto-logs in from. Home
# Assistant binds to all interfaces with a dual-stack socket, so IPv4 loopback
# connections arrive as the IPv4-mapped form ``::ffff:127.0.0.1``.
TRUSTED_LOOPBACK_NETWORKS = ["127.0.0.1/32", "::1/128", "::ffff:127.0.0.1/128"]


def auth_provider_configs() -> list[dict[str, Any]]:
    """Return the auth providers shared by the guide and sim runners.

    The trusted_networks provider auto-logs in the single dev user for any
    loopback request, so the frontend completes its OAuth flow without minting
    tokens or injecting a bootstrap page. It must come first so the authorize
    page starts its flow by default; homeassistant stays as a username/password
    fallback.
    """
    return [
        {
            "type": "trusted_networks",
            "trusted_networks": TRUSTED_LOOPBACK_NETWORKS,
            "allow_bypass_login": True,
        },
        {"type": "homeassistant"},
    ]


async def ensure_dev_user(hass: HomeAssistant) -> None:
    """Idempotently ensure a single ``Test User`` with testuser/testpass exists.

    The trusted_networks provider only auto-logs in when exactly one non-system
    user is available, so this is the sole user created for both runners.
    """
    provider = hass.auth.get_auth_provider("homeassistant", None)
    if provider is None:
        msg = "Home Assistant auth provider is not configured"
        raise RuntimeError(msg)

    users = await hass.auth.async_get_users()
    for user in users:
        for credential in user.credentials:
            if credential.data.get("username") == "testuser":
                return

    await provider.async_add_auth("testuser", "testpass")  # pyright: ignore[reportAttributeAccessIssue]

    owner = next(
        (user for user in users if user.is_owner and not user.system_generated),
        None,
    )
    if owner is None:
        owner = await hass.auth.async_create_user(name="Test User", group_ids=["system-admin"])

    credential = Credentials(
        id="test-credential",
        auth_provider_type="homeassistant",
        auth_provider_id=None,
        data={"username": "testuser"},
        is_new=False,
    )
    await hass.auth.async_link_user(owner, credential)


def _find_free_port() -> int:
    """Find a free port on localhost."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.getsockname()[1]


async def _require_component(
    hass: HomeAssistant,
    domain: str,
    hass_config: dict[str, Any],
) -> None:
    """Set up a core component, failing fast when programmatic bootstrap cannot continue."""
    if not await async_setup_component(hass, domain, hass_config):
        msg = f"Failed to set up {domain} component"
        raise RuntimeError(msg)


async def _ensure_http_started(hass: HomeAssistant) -> None:
    """Start the HTTP server exactly once.

    Setting up the frontend normally starts the server through Home Assistant's
    ``async_when_setup_or_start`` lifecycle hook. That hook runs standalone but
    not under pytest, so we start it ourselves when it has not already bound.
    Guarding on the existing site avoids binding the socket twice, which would
    orphan the already-listening server behind a failed second bind.
    """
    if hass.http.site is None:
        await hass.http.start()


@dataclass
class ConfigReloadWait:
    """Handle for waiting on a config entry reload cycle."""

    reload_started: asyncio.Event
    reload_finished: asyncio.Event
    unsubscribe: Callable[[], None]


@dataclass
class LiveHomeAssistant:
    """A running Home Assistant instance with HTTP server.

    Provides methods to interact with the HA instance from outside
    the event loop thread.
    """

    hass: HomeAssistant
    url: str
    port: int
    loop: asyncio.AbstractEventLoop
    _stop_event: asyncio.Event

    def set_state(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Set an entity state."""

        async def _set() -> None:
            self.hass.states.async_set(entity_id, state, attributes or {})

        future = asyncio.run_coroutine_threadsafe(_set(), self.loop)
        future.result(timeout=5)

    def set_states(self, states: list[dict[str, Any]]) -> None:
        """Set multiple entity states."""

        async def _set_all() -> None:
            for state_data in states:
                self.hass.states.async_set(
                    state_data["entity_id"],
                    state_data["state"],
                    state_data.get("attributes", {}),
                )
            await self.hass.async_block_till_done()

        future = asyncio.run_coroutine_threadsafe(_set_all(), self.loop)
        future.result(timeout=30)

    def load_states_from_file(self, states_file: Path) -> None:
        """Load entity states from a JSON file."""
        with states_file.open(encoding="utf-8") as f:
            states = json.load(f)
        self.set_states(states)

    def begin_wait_for_config_reload(self) -> ConfigReloadWait:
        """Register listeners before an action that triggers a reload."""
        return self.run_coro(self._async_begin_wait_for_config_reload())

    def wait_for_config_reload(self, reload_wait: ConfigReloadWait) -> None:
        """Block until the config entry reload cycle completes."""
        self.run_coro(self._async_wait_for_config_reload(reload_wait), timeout=None)

    async def _async_begin_wait_for_config_reload(self) -> ConfigReloadWait:
        """Register a config entry state listener on the HA event loop.

        Committing a subentry schedules a full integration reload. We watch the
        entry's state transitions: ``reload_started`` is set on the first move
        away from LOADED, ``reload_finished`` once it is back to LOADED with a
        live coordinator (or lands in a terminal error state).
        """
        from custom_components.haeo.const import DOMAIN  # noqa: PLC0415

        entries = self.hass.config_entries.async_entries(DOMAIN)
        if not entries:
            msg = "HAEO config entry not found"
            raise RuntimeError(msg)
        entry = entries[0]

        reload_started = asyncio.Event()
        reload_finished = asyncio.Event()

        @callback
        def on_state_change() -> None:
            if entry.state in (
                ConfigEntryState.UNLOAD_IN_PROGRESS,
                ConfigEntryState.NOT_LOADED,
                ConfigEntryState.SETUP_IN_PROGRESS,
            ):
                reload_started.set()
            if entry.state in (ConfigEntryState.SETUP_ERROR, ConfigEntryState.FAILED_UNLOAD) or (
                reload_started.is_set() and self._entry_is_operational(entry)
            ):
                reload_finished.set()

        unsubscribe = entry.async_on_state_change(on_state_change)
        return ConfigReloadWait(reload_started, reload_finished, unsubscribe)

    async def _async_wait_for_config_reload(self, reload_wait: ConfigReloadWait) -> None:
        """Wait for the reload to start and complete without polling."""
        await reload_wait.reload_started.wait()
        await reload_wait.reload_finished.wait()
        reload_wait.unsubscribe()
        from custom_components.haeo.const import DOMAIN  # noqa: PLC0415

        entries = self.hass.config_entries.async_entries(DOMAIN)
        if entries and entries[0].state is not ConfigEntryState.LOADED:
            msg = f"HAEO config entry reload failed: {entries[0].state} ({entries[0].reason})"
            raise RuntimeError(msg)
        await self.hass.async_block_till_done()

    @staticmethod
    def _entry_is_operational(entry: Any) -> bool:
        """Return True when the HAEO entry finished setup and has a coordinator."""
        if entry.state is not ConfigEntryState.LOADED:
            return False
        runtime_data = entry.runtime_data
        return runtime_data is not None and runtime_data.coordinator is not None

    def run_coro(self, coro: Any, timeout: float | None = 30) -> Any:
        """Run a coroutine on the HA event loop.

        Args:
            coro: Coroutine to run
            timeout: Maximum seconds to wait; None waits indefinitely

        Returns:
            Result of the coroutine

        """
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=timeout)

    def wait_for_recorder(self, timeout: float = 30) -> None:
        """Flush pending state changes to the recorder database."""
        from pytest_homeassistant_custom_component.components.recorder.common import (  # noqa: PLC0415
            async_wait_recording_done,
        )

        future = asyncio.run_coroutine_threadsafe(async_wait_recording_done(self.hass), self.loop)
        future.result(timeout=timeout)

    def configure_context(self, context: BrowserContext, *, dark_mode: bool = False) -> None:
        """Apply browser preferences for a Playwright context.

        Authentication is automatic from loopback via the trusted_networks
        provider, so this only seeds the dark mode theme when requested.
        """
        if not dark_mode:
            return

        theme_data = {"theme": "default", "dark": True}
        context.add_init_script(
            f"localStorage.setItem('selectedTheme', JSON.stringify({json.dumps(theme_data)}));",
        )

    def call_service(
        self,
        domain: str,
        service: str,
        service_data: dict[str, Any] | None = None,
        *,
        blocking: bool = True,
    ) -> None:
        """Call a Home Assistant service."""

        async def _call() -> None:
            await self.hass.services.async_call(
                domain,
                service,
                service_data or {},
                blocking=blocking,
            )

        future = asyncio.run_coroutine_threadsafe(_call(), self.loop)
        future.result(timeout=10)

    def stop(self) -> None:
        """Signal the HA instance to stop via thread-safe call."""
        self.loop.call_soon_threadsafe(self._stop_event.set)


async def _setup_home_assistant_async(
    port: int,
    config_dir: str,
    *,
    timezone: str = "UTC",
) -> HomeAssistant:
    """Set up a Home Assistant instance with HTTP server and pre-authenticated user."""
    storage_dir = Path(config_dir) / ".storage"
    storage_dir.mkdir(exist_ok=True)
    onboarding_storage = storage_dir / "onboarding"
    onboarding_data = {
        "version": 4,
        "minor_version": 1,
        "key": "onboarding",
        "data": {"done": ["user", "core_config", "analytics", "integration"]},
    }
    onboarding_storage.write_text(json.dumps(onboarding_data))

    hass = HomeAssistant(config_dir)

    hass.config.location_name = "Test Home"
    hass.config.latitude = 32.87336
    hass.config.longitude = -117.22743
    hass.config.elevation = 0
    await hass.config.async_set_time_zone(timezone)
    hass.config.skip_pip = True
    hass.config.skip_pip_packages = []

    loader.async_setup(hass)

    hass.config_entries = ConfigEntries(hass, {"_": "placeholder"})

    entity.async_setup(hass)
    translation.async_setup(hass)

    await ar.async_load(hass)
    await cr.async_load(hass)
    await dr.async_load(hass)
    await er.async_load(hass)
    await fr.async_load(hass)
    await ir.async_load(hass)
    await lr.async_load(hass)
    await rs.async_load(hass)
    await hass.config_entries.async_initialize()

    hass.auth = await auth_manager_from_config(
        hass,
        provider_configs=auth_provider_configs(),
        module_configs=[],
    )
    await ensure_dev_user(hass)

    warnings.filterwarnings("ignore", category=DeprecationWarning, module="aiohttp")
    try:
        from aiohttp.web_exceptions import NotAppKeyWarning  # noqa: PLC0415

        warnings.filterwarnings("ignore", category=NotAppKeyWarning)
    except ImportError:
        pass

    await _require_component(hass, "http", {"http": {"server_port": port}})
    await _require_component(hass, "websocket_api", {})
    await _require_component(hass, "auth", {})
    await _require_component(hass, "onboarding", {})

    from homeassistant.components.onboarding import async_is_onboarded  # noqa: PLC0415

    if not async_is_onboarded(hass):
        msg = "Onboarding bypass failed - check storage file format and timing"
        raise RuntimeError(msg)

    # Setting up frontend starts the HTTP server (it is wired via
    # async_when_setup_or_start), so we must not start it again ourselves.
    await _require_component(hass, "frontend", {})
    await _require_component(hass, "config", {})

    from homeassistant.helpers.recorder import async_initialize_recorder  # noqa: PLC0415

    async_initialize_recorder(hass)
    await _require_component(hass, "recorder", {"recorder": {"commit_interval": 1}})

    await _require_component(hass, "calendar", {})
    await _require_component(hass, "local_calendar", {})

    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    await _ensure_http_started(hass)

    return hass


def _shutdown_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Close async generators and executors before tearing down the HA loop."""
    try:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
    except Exception:
        _LOGGER.debug("HA event loop shutdown encountered an error", exc_info=True)
    finally:
        loop.close()


def _run_hass_thread(
    port: int,
    config_dir: str,
    timezone: str,
    hass_holder: list[HomeAssistant],
    loop_holder: list[asyncio.AbstractEventLoop],
    ready_event: threading.Event,
    async_stop_event_holder: list[asyncio.Event],
    error_holder: list[Exception],
) -> None:
    """Run Home Assistant in a thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop_holder.append(loop)

    async def _run() -> None:
        async_stop_event = asyncio.Event()
        async_stop_event_holder.append(async_stop_event)

        try:
            hass = await _setup_home_assistant_async(
                port,
                config_dir,
                timezone=timezone,
            )
            hass_holder.append(hass)
            ready_event.set()

            await async_stop_event.wait()
            await hass.async_block_till_done(wait_background_tasks=True)
            await hass.async_stop(force=True)
            await hass.async_block_till_done(wait_background_tasks=True)
            await asyncio.sleep(0)

        except Exception as e:
            error_holder.append(e)
            ready_event.set()

    try:
        loop.run_until_complete(_run())
    finally:
        _shutdown_event_loop(loop)


@contextmanager
def live_home_assistant(
    timeout: float = 60.0,
    *,
    environment: dict[str, Any] | None = None,
) -> Generator[LiveHomeAssistant]:
    """Context manager for a live Home Assistant instance."""
    scenario_environment = environment or {}
    timezone = str(scenario_environment.get("timezone", "UTC"))

    with tempfile.TemporaryDirectory(prefix="ha_live_") as tmp_dir:
        guide_config_dir = Path(tmp_dir)
        config_dir = str(guide_config_dir)

        custom_components = guide_config_dir / "custom_components"
        custom_components.mkdir()
        haeo_target = custom_components / "haeo"
        haeo_target.symlink_to(PROJECT_ROOT / "custom_components" / "haeo")

        port = _find_free_port()
        hass_holder: list[HomeAssistant] = []
        loop_holder: list[asyncio.AbstractEventLoop] = []
        error_holder: list[Exception] = []
        async_stop_event_holder: list[asyncio.Event] = []
        ready_event = threading.Event()

        thread = threading.Thread(
            target=_run_hass_thread,
            args=(
                port,
                config_dir,
                timezone,
                hass_holder,
                loop_holder,
                ready_event,
                async_stop_event_holder,
                error_holder,
            ),
            daemon=True,
        )
        thread.start()

        if not ready_event.wait(timeout=timeout):
            if loop_holder and async_stop_event_holder:
                loop_holder[0].call_soon_threadsafe(async_stop_event_holder[0].set)
            thread.join(timeout=5)
            msg = f"Home Assistant did not start within {timeout}s"
            raise TimeoutError(msg)

        if error_holder:
            if loop_holder and async_stop_event_holder:
                loop_holder[0].call_soon_threadsafe(async_stop_event_holder[0].set)
            thread.join(timeout=5)
            raise error_holder[0]

        hass = hass_holder[0]
        loop = loop_holder[0]
        async_stop_event = async_stop_event_holder[0]

        instance = LiveHomeAssistant(
            hass=hass,
            url=f"http://127.0.0.1:{port}",
            port=port,
            loop=loop,
            _stop_event=async_stop_event,
        )

        try:
            yield instance
        finally:
            instance.stop()
            thread.join(timeout=15)
