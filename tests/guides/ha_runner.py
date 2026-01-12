"""In-process Home Assistant runner for guide tests.

This module provides a way to run Home Assistant entirely in-process with
an HTTP server on an ephemeral port, allowing browser automation via Playwright.

The key insight is that we can:
1. Create a HomeAssistant instance with a minimal temp config directory
2. Set up the HTTP, frontend, and auth components programmatically
3. Load entity states directly via hass.states.async_set()
4. Run the event loop in a background thread
5. Access the HA instance from the main thread for Playwright automation
6. Pre-create an owner user and auth token to bypass onboarding UI

This avoids needing config files, YAML, or packages - just load states from JSON.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
import json
from pathlib import Path
import shutil
import socket
import tempfile
import threading
from typing import TYPE_CHECKING, Any
import warnings

from homeassistant import loader
from homeassistant.auth import auth_manager_from_config
from homeassistant.auth.models import Credentials
from homeassistant.config_entries import ConfigEntries
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
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

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext

# Path to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Client ID for refresh tokens (matches HA frontend)
CLIENT_ID = "http://127.0.0.1/"


def _find_free_port() -> int:
    """Find a free port on localhost."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


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
    access_token: str
    refresh_token_id: str
    _stop_event: threading.Event = field(default_factory=threading.Event)

    def set_state(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Set an entity state.

        Args:
            entity_id: Entity ID like "sensor.power"
            state: State value
            attributes: Optional attributes dict

        """

        async def _set() -> None:
            self.hass.states.async_set(entity_id, state, attributes or {})

        future = asyncio.run_coroutine_threadsafe(_set(), self.loop)
        future.result(timeout=5)

    def set_states(self, states: list[dict[str, Any]]) -> None:
        """Set multiple entity states.

        Args:
            states: List of dicts with entity_id, state, and optional attributes

        """

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
        """Load entity states from a JSON file.

        Args:
            states_file: Path to JSON file with state definitions

        """
        with states_file.open() as f:
            states = json.load(f)
        self.set_states(states)

    def run_coro(self, coro: Any, timeout: float = 30) -> Any:
        """Run a coroutine on the HA event loop.

        Args:
            coro: Coroutine to run
            timeout: Maximum seconds to wait

        Returns:
            Result of the coroutine

        """
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=timeout)

    def inject_auth(
        self, context: BrowserContext, *, dark_mode: bool = False
    ) -> None:
        """Inject authentication into a Playwright browser context.

        Sets up the Authorization header for all requests so HA frontend
        is pre-authenticated. Must be called before navigating to HA.

        Args:
            context: Playwright BrowserContext to inject auth into
            dark_mode: Whether to set dark mode theme preference

        """

        from playwright.sync_api import Request, Route

        # Add Authorization header to all API requests
        # HA frontend uses websocket for most communication but REST for some
        def add_auth_header(route: Route, request: Request) -> None:
            headers = {**request.headers, "Authorization": f"Bearer {self.access_token}"}
            route.continue_(headers=headers)

        context.route("**/*", add_auth_header)

        # Also set up localStorage token storage for frontend JS
        # HA stores auth data in localStorage under 'hassTokens'
        # Format matches what home-assistant-js-websocket expects
        token_data = {
            "hassUrl": self.url,
            "clientId": CLIENT_ID,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token_id,
            "token_type": "Bearer",
            "expires_in": 1800,  # 30 minutes
        }

        # Build localStorage init script
        theme_js = ""
        if dark_mode:
            # HA stores theme preference in localStorage as { theme: string, dark: boolean }
            theme_data = {"theme": "default", "dark": True}
            theme_js = f"""
            localStorage.setItem('selectedTheme', JSON.stringify({json.dumps(theme_data)}));
            """

        init_script = f"""
            localStorage.setItem('hassTokens', JSON.stringify({json.dumps(token_data)}));
            {theme_js}
        """
        context.add_init_script(init_script)

    def call_service(
        self,
        domain: str,
        service: str,
        service_data: dict[str, Any] | None = None,
        blocking: bool = True,
    ) -> None:
        """Call a Home Assistant service.

        Args:
            domain: Service domain (e.g., "frontend")
            service: Service name (e.g., "set_theme")
            service_data: Optional service data dict
            blocking: Whether to wait for service completion

        """

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
        """Signal the HA instance to stop."""
        self._stop_event.set()


async def _setup_home_assistant_async(
    port: int,
    config_dir: str,
) -> tuple[HomeAssistant, str]:
    """Set up a Home Assistant instance with HTTP server and pre-authenticated user.

    This creates a minimal HA instance with just the components needed
    for browser automation: http, frontend, auth, websocket_api.
    Onboarding is bypassed by creating an owner user programmatically.

    Returns:
        Tuple of (HomeAssistant instance, access_token for authentication)

    """
    # Pre-populate onboarding storage to mark all steps complete
    # This MUST be done BEFORE the HomeAssistant instance is created,
    # because the StoreManager scans the storage directory during initialization
    # and caches which files exist. If we write the file after that scan,
    # the onboarding component won't see it.
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

    # Basic configuration
    hass.config.location_name = "Test Home"
    hass.config.latitude = 32.87336
    hass.config.longitude = -117.22743
    hass.config.elevation = 0
    await hass.config.async_set_time_zone("UTC")
    hass.config.skip_pip = True
    hass.config.skip_pip_packages = []

    # Set up loader - don't set DATA_CUSTOM_COMPONENTS, let loader discover them
    loader.async_setup(hass)

    # Set up config entries
    hass.config_entries = ConfigEntries(hass, {"_": "placeholder"})
    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP,
        hass.config_entries._async_shutdown,
    )

    # Set up essential helpers
    entity.async_setup(hass)

    # Translation cache
    hass.data[translation.TRANSLATION_FLATTEN_CACHE] = translation._TranslationCache(hass)

    # Load registries
    await ar.async_load(hass)
    await cr.async_load(hass)
    await dr.async_load(hass)
    await er.async_load(hass)
    await fr.async_load(hass)
    await ir.async_load(hass)
    await lr.async_load(hass)
    await rs.async_load(hass)

    # Set up auth with homeassistant provider
    hass.auth = await auth_manager_from_config(
        hass,
        provider_configs=[{"type": "homeassistant"}],
        module_configs=[],
    )

    # Get the homeassistant auth provider to add a user with password
    provider = hass.auth.auth_providers[0]
    # Add user credentials to the provider's storage
    await provider.async_add_auth("testuser", "testpass")

    # Create owner user to bypass onboarding
    # First non-system user automatically becomes owner
    owner = await hass.auth.async_create_user(
        name="Test User",
        group_ids=["system-admin"],
    )

    # Create credential and link to user
    credential = Credentials(
        id="test-credential",
        auth_provider_type="homeassistant",
        auth_provider_id=None,
        data={"username": "testuser"},
        is_new=False,
    )
    await hass.auth.async_link_user(owner, credential)

    # Create refresh token and access token
    refresh_token = await hass.auth.async_create_refresh_token(
        owner,
        CLIENT_ID,
        credential=credential,
    )
    access_token = hass.auth.async_create_access_token(refresh_token)
    # Store refresh token ID for frontend auth
    refresh_token_id = refresh_token.id

    # Set up HTTP on ephemeral port
    http_config = {
        "server_port": port,
    }

    # Suppress aiohttp.web_exceptions.NotAppKeyWarning which is raised as an error
    # in newer versions of aiohttp when HA sets app["hass"] = hass
    # This is a compatibility issue between HA and newer aiohttp versions
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="aiohttp")
    try:
        from aiohttp.web_exceptions import NotAppKeyWarning

        warnings.filterwarnings("ignore", category=NotAppKeyWarning)
    except ImportError:
        pass  # Older aiohttp doesn't have this

    # Set up components in order (onboarding will see all steps done and skip
    # because we pre-populated the storage file)
    assert await async_setup_component(hass, "http", {"http": http_config})
    assert await async_setup_component(hass, "websocket_api", {})
    assert await async_setup_component(hass, "auth", {})
    assert await async_setup_component(hass, "onboarding", {})

    # Verify onboarding is bypassed
    from homeassistant.components.onboarding import async_is_onboarded

    if not async_is_onboarded(hass):
        msg = "Onboarding bypass failed - check storage file format and timing"
        raise RuntimeError(msg)

    assert await async_setup_component(hass, "frontend", {})
    assert await async_setup_component(hass, "config", {})

    # Mark as running
    hass.set_state(CoreState.running)

    # Start the HTTP server
    if hass.http is not None:
        await hass.http.start()

    return hass, access_token, refresh_token_id


def _run_hass_thread(
    port: int,
    config_dir: str,
    hass_holder: list[HomeAssistant],
    token_holder: list[tuple[str, str]],
    loop_holder: list[asyncio.AbstractEventLoop],
    ready_event: threading.Event,
    stop_event: threading.Event,
    error_holder: list[Exception],
) -> None:
    """Run Home Assistant in a thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop_holder.append(loop)

    async def _run() -> None:
        try:
            hass, access_token, refresh_token_id = await _setup_home_assistant_async(port, config_dir)
            hass_holder.append(hass)
            token_holder.append((access_token, refresh_token_id))
            ready_event.set()

            # Wait for stop signal
            while not stop_event.is_set():
                await asyncio.sleep(0.1)

            # Shutdown - async_stop will handle HTTP server via event handler
            await hass.async_stop(force=True)

        except Exception as e:
            error_holder.append(e)
            ready_event.set()  # Unblock the main thread

    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()


@contextmanager
def live_home_assistant(
    timeout: float = 60.0,
) -> Generator[LiveHomeAssistant]:
    """Context manager for a live Home Assistant instance.

    Starts HA on an ephemeral port in a background thread and yields
    a LiveHomeAssistant instance for interaction. The instance includes
    a pre-authenticated access_token for browser automation.

    Args:
        timeout: Maximum seconds to wait for HA to start

    Yields:
        LiveHomeAssistant instance with access_token for auth

    Example:
        with live_home_assistant() as hass:
            hass.set_states([
                {"entity_id": "sensor.power", "state": "1500", "attributes": {...}}
            ])
            # Inject auth into Playwright context
            hass.inject_auth(browser_context)
            # Use Playwright to interact with hass.url

    """
    port = _find_free_port()

    # Create a temporary config directory (HA requires one even if minimal)
    with tempfile.TemporaryDirectory(prefix="haeo_guide_") as temp_dir:
        config_dir = temp_dir

        # Create custom_components symlink for HAEO
        custom_components = Path(temp_dir) / "custom_components"
        custom_components.mkdir()
        haeo_source = PROJECT_ROOT / "custom_components" / "haeo"
        haeo_target = custom_components / "haeo"
        haeo_target.symlink_to(haeo_source)

        # Copy SingleFile bundle to www directory for HTML captures
        www_dir = Path(temp_dir) / "www"
        www_dir.mkdir()
        singlefile_bundle = PROJECT_ROOT / "node_modules" / "single-file-cli" / "lib" / "single-file-bundle.js"
        if singlefile_bundle.exists():
            shutil.copy2(singlefile_bundle, www_dir / "single-file-bundle.js")

        hass_holder: list[HomeAssistant] = []
        token_holder: list[tuple[str, str]] = []
        loop_holder: list[asyncio.AbstractEventLoop] = []
        error_holder: list[Exception] = []
        ready_event = threading.Event()
        stop_event = threading.Event()

        thread = threading.Thread(
            target=_run_hass_thread,
            args=(
                port,
                config_dir,
                hass_holder,
                token_holder,
                loop_holder,
                ready_event,
                stop_event,
                error_holder,
            ),
            daemon=True,
        )
        thread.start()

        # Wait for HA to be ready
        if not ready_event.wait(timeout=timeout):
            stop_event.set()
            thread.join(timeout=5)
            msg = f"Home Assistant did not start within {timeout}s"
            raise TimeoutError(msg)

        # Check for errors during startup
        if error_holder:
            stop_event.set()
            thread.join(timeout=5)
            raise error_holder[0]

        hass = hass_holder[0]
        access_token, refresh_token_id = token_holder[0]
        loop = loop_holder[0]

        instance = LiveHomeAssistant(
            hass=hass,
            url=f"http://127.0.0.1:{port}",
            port=port,
            loop=loop,
            access_token=access_token,
            refresh_token_id=refresh_token_id,
            _stop_event=stop_event,
        )

        try:
            yield instance
        finally:
            stop_event.set()
            thread.join(timeout=10)


def load_states_from_json(path: Path) -> list[dict[str, Any]]:
    """Load entity states from a JSON file.

    Args:
        path: Path to JSON file

    Returns:
        List of state dictionaries

    """
    with path.open() as f:
        return json.load(f)
