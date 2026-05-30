"""In-process Home Assistant runner for dev tools and guide tests.

This module provides a way to run Home Assistant entirely in-process with
an HTTP server on an ephemeral port, allowing browser automation via Playwright
or interactive development via ``uv run sim``.

The key insight is that we can:
1. Create a HomeAssistant instance with a minimal temp config directory
2. Set up the HTTP, frontend, and auth components programmatically
3. Load entity states directly via hass.states.async_set()
4. Run the event loop in a background thread
5. Access the HA instance from the main thread for automation
6. Pre-create an owner user and auth token to bypass onboarding UI
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from contextlib import closing, contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import socket
import tempfile
import threading
from types import MappingProxyType
from typing import TYPE_CHECKING, Any
import warnings

from homeassistant import loader
from homeassistant.auth import auth_manager_from_config
from homeassistant.auth.models import Credentials
from homeassistant.config_entries import ConfigEntries, ConfigSubentry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CoreState, HomeAssistant
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
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import MIGRATION_MINOR_VERSION
from custom_components.haeo.const import DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.const import (
    CONF_ELEMENT_TYPE,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
)
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON, HUB_SECTION_TIERS

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext

PROJECT_ROOT = Path(__file__).parent.parent


def _find_free_port() -> int:
    """Find a free port on localhost."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.getsockname()[1]


def _client_id(port: int) -> str:
    """Return the OAuth client ID for a live Home Assistant instance."""
    return f"http://127.0.0.1:{port}/"


def _write_onboarding_storage(config_dir: str) -> None:
    """Mark onboarding complete before Home Assistant initializes storage caches."""
    storage_dir = Path(config_dir) / ".storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    onboarding_storage = storage_dir / "onboarding"
    onboarding_data = {
        "version": 4,
        "minor_version": 1,
        "key": "onboarding",
        "data": {"done": ["user", "core_config", "analytics", "integration"]},
    }
    onboarding_storage.write_text(json.dumps(onboarding_data))


def _find_dev_user(users: list[Any]) -> Any | None:
    """Return the developer user if one already exists in storage."""
    for user in users:
        if user.system_generated:
            continue
        if user.name == "Test User":
            return user
        for credential in user.credentials:
            if credential.data.get("username") == "testuser":
                return user

    for user in users:
        if user.is_owner and not user.system_generated:
            return user

    return None


def _find_testuser(users: list[Any]) -> tuple[Any, Credentials] | None:
    """Return the user and credential for testuser when already linked."""
    for user in users:
        for credential in user.credentials:
            if credential.data.get("username") == "testuser":
                return user, credential
    return None


async def _ensure_dev_auth(hass: HomeAssistant, *, port: int) -> tuple[str, str]:
    """Ensure onboarding is bypassed and testuser credentials exist."""
    from homeassistant.components.onboarding import async_is_onboarded  # noqa: PLC0415

    if not async_is_onboarded(hass):
        msg = "Onboarding bypass failed - check storage file format and timing"
        raise RuntimeError(msg)

    client_id = _client_id(port)
    provider = hass.auth.auth_providers[0]
    users = await hass.auth.async_get_users()
    linked = _find_testuser(users)

    if linked is None:
        await provider.async_add_auth("testuser", "testpass")  # pyright: ignore[reportAttributeAccessIssue]
        owner = _find_dev_user(users)
        if owner is None:
            owner = await hass.auth.async_create_user(
                name="Test User",
                group_ids=["system-admin"],
            )
        credential = Credentials(
            id="test-credential",
            auth_provider_type="homeassistant",
            auth_provider_id=None,
            data={"username": "testuser"},
            is_new=False,
        )
        await hass.auth.async_link_user(owner, credential)
    else:
        owner, credential = linked

    refresh_token = await hass.auth.async_create_refresh_token(
        owner,
        client_id,
        credential=credential,
    )
    access_token = hass.auth.async_create_access_token(refresh_token)
    return access_token, refresh_token.token


AUTH_BOOTSTRAP_FILENAME = "haeo-sim-login.html"


def _ensure_haeo_symlink(config_dir: Path) -> None:
    """Ensure custom_components/haeo symlink exists in the config directory."""
    custom_components = config_dir / "custom_components"
    custom_components.mkdir(parents=True, exist_ok=True)
    haeo_target = custom_components / "haeo"
    if not haeo_target.exists():
        haeo_target.symlink_to(PROJECT_ROOT / "custom_components" / "haeo")


@dataclass
class LiveHomeAssistant:
    """A running Home Assistant instance with HTTP server."""

    hass: HomeAssistant
    url: str
    port: int
    loop: asyncio.AbstractEventLoop
    access_token: str
    refresh_token: str
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

    def run_coro(self, coro: Any, timeout: float | None = 30) -> Any:
        """Run a coroutine on the HA event loop."""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=timeout)

    def wait_for_recorder(self, timeout: float = 30) -> None:
        """Flush pending state changes to the recorder database."""
        from pytest_homeassistant_custom_component.components.recorder.common import (  # noqa: PLC0415
            async_wait_recording_done,
        )

        future = asyncio.run_coroutine_threadsafe(async_wait_recording_done(self.hass), self.loop)
        future.result(timeout=timeout)

    def inject_auth(self, context: BrowserContext, *, dark_mode: bool = False) -> None:
        """Inject authentication into a Playwright browser context."""
        from playwright.sync_api import Request, Route  # noqa: PLC0415

        def add_auth_header(route: Route, request: Request) -> None:
            headers = {
                **request.headers,
                "Authorization": f"Bearer {self.access_token}",
            }
            route.continue_(headers=headers)

        context.route("**/*", add_auth_header)

        token_data = _auth_token_data(self)

        theme_js = ""
        if dark_mode:
            theme_data = {"theme": "default", "dark": True}
            theme_js = f"""
            localStorage.setItem('selectedTheme', JSON.stringify({json.dumps(theme_data)}));
            """

        init_script = f"""
            localStorage.setItem('hassTokens', JSON.stringify({json.dumps(token_data)}));
            {theme_js}
        """
        context.add_init_script(init_script)

    def publish_browser_auth(self) -> str:
        """Write a same-origin bootstrap page that stores auth tokens for the frontend."""
        config_dir = Path(self.hass.config.config_dir)
        www_dir = config_dir / "www"
        www_dir.mkdir(parents=True, exist_ok=True)

        token_data = _auth_token_data(self)
        bootstrap_path = www_dir / AUTH_BOOTSTRAP_FILENAME
        bootstrap_path.write_text(
            f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>HAEO Sim Login</title>
  </head>
  <body>
    <script>
      localStorage.setItem("hassTokens", JSON.stringify({json.dumps(token_data)}));
      window.location.replace({json.dumps(f"{self.url}/")});
    </script>
  </body>
</html>
""",
            encoding="utf-8",
        )
        return f"{self.url}/local/{AUTH_BOOTSTRAP_FILENAME}"

    def remove_browser_auth(self) -> None:
        """Remove the temporary browser auth bootstrap page."""
        bootstrap_path = Path(self.hass.config.config_dir) / "www" / AUTH_BOOTSTRAP_FILENAME
        if bootstrap_path.exists():
            bootstrap_path.unlink()

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


def _auth_token_data(live_hass: LiveHomeAssistant) -> dict[str, object]:
    """Return frontend localStorage token payload for a live instance."""
    return {
        "hassUrl": live_hass.url,
        "clientId": _client_id(live_hass.port),
        "access_token": live_hass.access_token,
        "refresh_token": live_hass.refresh_token,
        "token_type": "Bearer",
        "expires_in": 1800,
    }


async def setup_haeo_entry(hass: HomeAssistant, scenario_config: dict[str, Any]) -> MockConfigEntry:
    """Create and set up a HAEO hub config entry from scenario config data."""
    tiers_data = scenario_config.get("tiers") or scenario_config
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {CONF_NAME: "Test Hub"},
            HUB_SECTION_TIERS: {
                CONF_TIER_1_COUNT: tiers_data["tier_1_count"],
                CONF_TIER_1_DURATION: tiers_data["tier_1_duration"],
                CONF_TIER_2_COUNT: tiers_data.get("tier_2_count", 0),
                CONF_TIER_2_DURATION: tiers_data.get("tier_2_duration", 5),
                CONF_TIER_3_COUNT: tiers_data.get("tier_3_count", 0),
                CONF_TIER_3_DURATION: tiers_data.get("tier_3_duration", 30),
                CONF_TIER_4_COUNT: tiers_data.get("tier_4_count", 0),
                CONF_TIER_4_DURATION: tiers_data.get("tier_4_duration", 60),
            },
            HUB_SECTION_ADVANCED: {},
        },
        version=scenario_config.get("version", 1),
        minor_version=scenario_config.get("minor_version", MIGRATION_MINOR_VERSION),
    )
    mock_config_entry.add_to_hass(hass)

    for name, config in scenario_config["participants"].items():
        subentry = ConfigSubentry(
            data=MappingProxyType(config),
            subentry_type=config[CONF_ELEMENT_TYPE],
            title=name,
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(mock_config_entry, subentry)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return mock_config_entry


async def _setup_home_assistant_async(
    port: int,
    config_dir: str,
    *,
    environment: dict[str, Any] | None = None,
) -> tuple[HomeAssistant, str, str]:
    """Set up a Home Assistant instance with HTTP server and pre-authenticated user."""
    scenario_environment = environment or {}
    timezone = scenario_environment.get("timezone", "UTC")

    _write_onboarding_storage(config_dir)

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
    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP,
        hass.config_entries._async_shutdown,
    )

    entity.async_setup(hass)
    hass.data[translation.TRANSLATION_FLATTEN_CACHE] = translation._TranslationCache(hass)

    await ar.async_load(hass)
    await cr.async_load(hass)
    await dr.async_load(hass)
    await er.async_load(hass)
    await fr.async_load(hass)
    await ir.async_load(hass)
    await lr.async_load(hass)
    await rs.async_load(hass)

    hass.auth = await auth_manager_from_config(
        hass,
        provider_configs=[{"type": "homeassistant"}],
        module_configs=[],
    )

    http_config = {
        "server_port": port,
    }

    warnings.filterwarnings("ignore", category=DeprecationWarning, module="aiohttp")
    try:
        from aiohttp.web_exceptions import NotAppKeyWarning  # noqa: PLC0415

        warnings.filterwarnings("ignore", category=NotAppKeyWarning)
    except ImportError:
        pass

    assert await async_setup_component(hass, "http", {"http": http_config})
    assert await async_setup_component(hass, "websocket_api", {})
    assert await async_setup_component(hass, "auth", {})
    assert await async_setup_component(hass, "onboarding", {})

    access_token, refresh_token_value = await _ensure_dev_auth(hass, port=port)

    assert await async_setup_component(hass, "frontend", {})
    assert await async_setup_component(hass, "config", {})

    from homeassistant.helpers.recorder import async_initialize_recorder  # noqa: PLC0415

    async_initialize_recorder(hass)
    assert await async_setup_component(hass, "recorder", {"recorder": {"commit_interval": 1}})

    assert await async_setup_component(hass, "calendar", {})
    assert await async_setup_component(hass, "local_calendar", {})

    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    await hass.http.start()

    return hass, access_token, refresh_token_value


def _run_hass_thread(
    port: int,
    config_dir: str,
    environment: dict[str, Any] | None,
    hass_holder: list[HomeAssistant],
    token_holder: list[tuple[str, str]],
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
            hass, access_token, refresh_token_value = await _setup_home_assistant_async(
                port,
                config_dir,
                environment=environment,
            )
            hass_holder.append(hass)
            token_holder.append((access_token, refresh_token_value))
            ready_event.set()

            await async_stop_event.wait()
            await hass.async_stop(force=True)

        except Exception as e:
            error_holder.append(e)
            ready_event.set()

    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()


def _start_live_home_assistant(
    config_dir: Path,
    *,
    timeout: float,
    port: int | None,
    environment: dict[str, Any] | None,
) -> tuple[LiveHomeAssistant, threading.Thread]:
    """Start HA in a background thread and return the live instance."""
    _ensure_haeo_symlink(config_dir)
    resolved_port = port if port is not None else _find_free_port()
    hass_holder: list[HomeAssistant] = []
    token_holder: list[tuple[str, str]] = []
    loop_holder: list[asyncio.AbstractEventLoop] = []
    error_holder: list[Exception] = []
    async_stop_event_holder: list[asyncio.Event] = []
    ready_event = threading.Event()

    thread = threading.Thread(
        target=_run_hass_thread,
        args=(
            resolved_port,
            str(config_dir),
            environment,
            hass_holder,
            token_holder,
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
    access_token, refresh_token_value = token_holder[0]
    loop = loop_holder[0]
    async_stop_event = async_stop_event_holder[0]

    instance = LiveHomeAssistant(
        hass=hass,
        url=f"http://127.0.0.1:{resolved_port}",
        port=resolved_port,
        loop=loop,
        access_token=access_token,
        refresh_token=refresh_token_value,
        _stop_event=async_stop_event,
    )
    return instance, thread


def _stop_live_home_assistant(instance: LiveHomeAssistant, thread: threading.Thread) -> None:
    """Stop a live Home Assistant instance."""
    instance.loop.call_soon_threadsafe(instance._stop_event.set)
    thread.join(timeout=10)


@contextmanager
def live_home_assistant(
    timeout: float = 60.0,
    *,
    config_dir: Path | None = None,
    port: int | None = None,
    environment: dict[str, Any] | None = None,
) -> Generator[LiveHomeAssistant]:
    """Context manager for a live Home Assistant instance.

    Args:
        timeout: Maximum seconds to wait for HA to start.
        config_dir: Optional persistent config directory. When omitted, a temporary
            directory is created and removed on exit.
        port: Optional fixed HTTP port. When omitted, an ephemeral port is chosen.
        environment: Optional scenario environment dict. When provided, ``timezone``
            is applied during bootstrap and onboarding/auth are prepared for dev use.

    """
    if config_dir is None:
        with tempfile.TemporaryDirectory(prefix="ha_live_") as tmp_dir:
            instance, thread = _start_live_home_assistant(
                Path(tmp_dir),
                timeout=timeout,
                port=port,
                environment=environment,
            )
            try:
                yield instance
            finally:
                _stop_live_home_assistant(instance, thread)
    else:
        config_dir.mkdir(parents=True, exist_ok=True)
        instance, thread = _start_live_home_assistant(
            config_dir,
            timeout=timeout,
            port=port,
            environment=environment,
        )
        try:
            yield instance
        finally:
            _stop_live_home_assistant(instance, thread)
