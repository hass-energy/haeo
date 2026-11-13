"""Sim-specific extensions for the live Home Assistant runner.

``uv run sim`` uses persistent config directories, port-specific auth client IDs,
optional HAEO setup from scenario config, and a trusted-networks auth provider so
the browser is always logged in from loopback. Guide tests continue to use
``tools.live_hass`` directly.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
import tempfile
import threading
from types import MappingProxyType

from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.util.json import JsonValueType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import MIGRATION_MINOR_VERSION
from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from tools.live_hass import PROJECT_ROOT, LiveHomeAssistant, _find_free_port, _setup_home_assistant_async


def _ensure_haeo_symlink(config_dir: Path) -> None:
    """Ensure custom_components/haeo symlink exists in the config directory."""
    custom_components = config_dir / "custom_components"
    custom_components.mkdir(parents=True, exist_ok=True)
    haeo_target = custom_components / "haeo"
    if not haeo_target.exists():
        haeo_target.symlink_to(PROJECT_ROOT / "custom_components" / "haeo")


async def _remove_haeo_entries(hass: HomeAssistant) -> None:
    """Remove HAEO config entries left from prior ``uv run sim`` sessions."""
    for entry in list(hass.config_entries.async_entries(DOMAIN)):
        if entry.state in (ConfigEntryState.LOADED, ConfigEntryState.SETUP_IN_PROGRESS):
            await hass.config_entries.async_unload(entry.entry_id)
        await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)


async def wait_for_sim_idle(hass: HomeAssistant) -> None:
    """Wait until scheduled setup/reload work on the HA loop has finished."""
    await hass.async_block_till_done(wait_background_tasks=True)


# Scenario config keys that describe the scenario rather than the hub's config entry data
_NON_HUB_SCENARIO_KEYS = frozenset({"participants", "version", "minor_version", "update_interval_minutes"})


def _require_dict(value: JsonValueType, context: str) -> dict[str, JsonValueType]:
    """Narrow a scenario JSON value to a dict, with a readable failure."""
    if not isinstance(value, dict):
        msg = f"Scenario {context} must be an object, got {type(value).__name__}"
        raise TypeError(msg)
    return value


async def setup_haeo_entry(hass: HomeAssistant, scenario_config: dict[str, JsonValueType]) -> MockConfigEntry:
    """Create and set up a HAEO hub config entry from scenario config data."""
    await _remove_haeo_entries(hass)

    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={key: value for key, value in scenario_config.items() if key not in _NON_HUB_SCENARIO_KEYS},
        version=version if isinstance(version := scenario_config.get("version", 1), int) else 1,
        minor_version=(
            minor
            if isinstance(minor := scenario_config.get("minor_version", MIGRATION_MINOR_VERSION), int)
            else MIGRATION_MINOR_VERSION
        ),
    )
    mock_config_entry.add_to_hass(hass)

    participants = _require_dict(scenario_config["participants"], "participants")
    for name, raw_config in participants.items():
        config = _require_dict(raw_config, f"participant {name!r}")
        subentry = ConfigSubentry(
            data=MappingProxyType(config),
            subentry_type=str(config[CONF_ELEMENT_TYPE]),
            title=name,
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(mock_config_entry, subentry)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return mock_config_entry


async def _setup_sim_home_assistant_async(
    port: int,
    config_dir: str,
    *,
    timezone: str,
    currency: str,
) -> HomeAssistant:
    """Bootstrap Home Assistant for sim without the HAEO entries of earlier runs."""
    hass = await _setup_home_assistant_async(port, config_dir, timezone=timezone, currency=currency)
    # Drop entries persisted from earlier sim runs so we do not boot into a
    # pile of parallel HAEO setups that race the browser auto-login redirect.
    await _remove_haeo_entries(hass)
    return hass


def _run_sim_hass_thread(
    port: int,
    config_dir: str,
    timezone: str,
    currency: str,
    hass_holder: list[HomeAssistant],
    loop_holder: list[asyncio.AbstractEventLoop],
    ready_event: threading.Event,
    async_stop_event_holder: list[asyncio.Event],
    error_holder: list[Exception],
) -> None:
    """Run sim Home Assistant in a thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop_holder.append(loop)

    async def _run() -> None:
        async_stop_event = asyncio.Event()
        async_stop_event_holder.append(async_stop_event)

        try:
            hass = await _setup_sim_home_assistant_async(
                port,
                config_dir,
                timezone=timezone,
                currency=currency,
            )
            hass_holder.append(hass)
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


def _start_sim_home_assistant(
    config_dir: Path,
    *,
    timeout: float,
    port: int | None,
    timezone: str,
    currency: str,
) -> tuple[LiveHomeAssistant, threading.Thread]:
    """Start sim HA in a background thread and return the live instance."""
    _ensure_haeo_symlink(config_dir)
    resolved_port = port if port is not None else _find_free_port()
    hass_holder: list[HomeAssistant] = []
    loop_holder: list[asyncio.AbstractEventLoop] = []
    error_holder: list[Exception] = []
    async_stop_event_holder: list[asyncio.Event] = []
    ready_event = threading.Event()

    thread = threading.Thread(
        target=_run_sim_hass_thread,
        args=(
            resolved_port,
            str(config_dir),
            timezone,
            currency,
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
        url=f"http://127.0.0.1:{resolved_port}",
        port=resolved_port,
        loop=loop,
        _stop_event=async_stop_event,
    )
    return instance, thread


@contextmanager
def live_sim_home_assistant(
    timeout: float = 60.0,
    *,
    config_dir: Path | None = None,
    port: int | None = None,
    environment: dict[str, JsonValueType] | None = None,
) -> Generator[LiveHomeAssistant]:
    """Context manager for a sim Home Assistant instance with optional persistent config."""
    scenario_environment = environment or {}
    timezone = str(scenario_environment.get("timezone", "UTC"))
    # Home Assistant defaults to euros, so a missing currency reads as Australian dollars
    currency = str(scenario_environment.get("currency", "AUD"))

    if config_dir is None:
        with tempfile.TemporaryDirectory(prefix="ha_live_") as tmp_dir:
            instance, thread = _start_sim_home_assistant(
                Path(tmp_dir),
                timeout=timeout,
                port=port,
                timezone=timezone,
                currency=currency,
            )
            try:
                yield instance
            finally:
                instance.stop()
                thread.join(timeout=10)
    else:
        config_dir.mkdir(parents=True, exist_ok=True)
        instance, thread = _start_sim_home_assistant(
            config_dir,
            timeout=timeout,
            port=port,
            timezone=timezone,
            currency=currency,
        )
        try:
            yield instance
        finally:
            instance.stop()
            thread.join(timeout=10)
